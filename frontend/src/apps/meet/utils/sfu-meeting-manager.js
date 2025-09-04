import { nextTick } from "vue";
import {
	createTransport,
	getRouterCapabilities,
	publishAudio,
	publishVideo,
	requestExistingProducers,
	subscribeToProducer,
} from "../mediasoup-client.js";
import { getSFUClient } from "./sfu-client.js";

/**
 * SFU Meeting Manager
 * Handles all SFU-related operations for video meetings
 */
export class SFUMeetingManager {
	constructor() {
		this.sfuClient = null;
		this.meetingId = null;
		this.currentUser = { value: null };
		// Always initialize participants/consumers/remoteVideos as refs with a value property
		this.participants = { value: new Map() };
		this.consumers = { value: new Map() };
		this.remoteVideos = { value: new Map() };
		this.eventHandlers = {};
		this.isConnected = false;
		this.initialSyncInProgress = false;
		this.bufferedProducerEvents = [];
		this.screenShareProducers = new Map(); // producerId -> { participantId }
	}

	/**
	 * Initialize the SFU manager with required dependencies
	 */
	initialize(options) {
		this.meetingId = options.meetingId;
		// Always ensure currentUser is an object with a value property
		if (
			options.currentUser &&
			typeof options.currentUser === "object" &&
			"value" in options.currentUser
		) {
			this.currentUser = options.currentUser;
		} else if (
			typeof options.currentUser === "object" &&
			options.currentUser !== null
		) {
			this.currentUser = { value: options.currentUser };
		} else {
			this.currentUser = { value: options.currentUser || null };
		}
		// Ensure participants is always an object with a value property
		if (
			options.participants &&
			typeof options.participants === "object" &&
			"value" in options.participants
		) {
			this.participants = options.participants;
		} else {
			this.participants = { value: options.participants || new Map() };
		}
		this.consumers = options.consumers ||
			this.consumers || { value: new Map() };
		this.remoteVideos = options.remoteVideos ||
			this.remoteVideos || { value: new Map() };
		this.eventHandlers = options.eventHandlers || {};
	}

	/**
	 * Connect to the SFU server
	 */
	async connect() {
		try {
			console.log("🔗 Connecting to SFU server...");
			this.sfuClient = getSFUClient();
			await this.sfuClient.connect(this.meetingId);
			this.isConnected = true;
			console.log("✅ Connected to SFU");

			// Set up SFU event handlers
			this.setupSFUEventHandlers();

			return true;
		} catch (error) {
			console.error("❌ Failed to connect to SFU:", error);
			throw error;
		}
	}

	/**
	 * Initialize MediaSoup device with router capabilities
	 */
	async initializeDevice() {
		try {
			await getRouterCapabilities(this.meetingId);
			return true;
		} catch (error) {
			console.error("❌ Failed to initialize MediaSoup device:", error);
			throw error;
		}
	}

	/**
	 * Create receive transport for incoming media
	 */
	async createReceiveTransport() {
		try {
			const { transport: recvTransport } = await createTransport(
				this.meetingId,
				"recv",
			);

			// Wait a moment for transport to be ready
			await new Promise((resolve) => setTimeout(resolve, 200));

			// Verify transport is in good state before proceeding
			if (recvTransport.connectionState === "failed") {
				throw new Error("Receive transport failed immediately after creation");
			}

			return recvTransport;
		} catch (error) {
			console.warn("⚠️ Failed to create receive transport:", error);
			console.warn("⚠️ Will attempt to create receive transport when needed");
			return null;
		}
	}

	/**
	 * Publish local media streams
	 */
	async publishMedia(localStream, options = {}) {
		const {
			publishVideo: shouldPublishVideo = true,
			publishAudio: shouldPublishAudio = true,
		} = options;
		const results = {};

		try {
			const attemptPublish = async (label) => {
				const out = {};
				if (localStream && shouldPublishVideo) {
					out.videoProducer = await publishVideo(this.meetingId, localStream);
				}
				if (localStream && shouldPublishAudio) {
					out.audioProducer = await publishAudio(this.meetingId, localStream);
				}
				return out;
			};

			// First attempt
			Object.assign(results, await attemptPublish("attempt-1"));

			// If nothing created, retry once after a short delay
			if (!results.videoProducer && !results.audioProducer) {
				console.warn(
					"⚠️ No producers created on first attempt, retrying shortly...",
				);
				await new Promise((r) => setTimeout(r, 400));
				const second = await attemptPublish("attempt-2");
				Object.assign(results, second);
			}

			if (!results.videoProducer && !results.audioProducer) {
				console.warn("⚠️ No producers created by publishMedia after retries");
			}

			return results;
		} catch (error) {
			console.error("❌ Failed to publish media:", error);
			throw error;
		}
	}

	/**
	 * Request and setup existing participants
	 */
	async setupExistingParticipants() {
		try {
			this.initialSyncInProgress = true;
			// Seed participants list from SFU room roster
			try {
				const roster = await this.sfuClient.getRoomParticipants();
				if (Array.isArray(roster)) {
					for (const p of roster) {
						if (
							p.user_id &&
							p.user_id !==
								(this.currentUser &&
								typeof this.currentUser === "object" &&
								"value" in this.currentUser
									? this.currentUser.value?.user_id
									: null)
						) {
							const existing = this.participants.value.get(p.user_id);
							if (!existing) {
								this.participants.value.set(p.user_id, {
									user_id: p.user_id,
									user_name: p.info?.name || p.user_id,
									avatar: p.info?.avatar || null,
									initials: (p.info?.name || p.user_id)
										.split(" ")
										.map((n) => n[0])
										.join("")
										.toUpperCase()
										.slice(0, 2),
									audio_enabled:
										typeof p.info?.audio_enabled === "boolean"
											? p.info.audio_enabled
											: false,
									// Never trust roster for camera state; set false until a non-screen video producer is observed
									video_enabled: false,
								});
							}
						}
					}
					this.participants.value = new Map(this.participants.value);
				}
			} catch (e) {
				console.warn("Failed to fetch room roster:", e?.message || e);
			}
			// Request existing producers from the SFU
			await this.requestExistingProducers();

			// Reconcile: ensure all consumers are attached based on current flags/tiles
			try {
				await this.reconcileAllAttachments();
			} catch (e) {
				console.warn("Reconcile attachments failed:", e?.message || e);
			}

			// Flush any producers announced during initial sync that we skipped
			try {
				await this.flushBufferedProducers();
			} catch (e) {
				console.warn("Flush buffered producers failed:", e?.message || e);
			}

			this.initialSyncInProgress = false;

			return true;
		} catch (error) {
			console.error("❌ Error setting up existing participants:", error);
			throw error;
		}
	}

	/**
	 * Subscribe/attach any producer_created events buffered during initial sync
	 */
	async flushBufferedProducers() {
		if (!this.bufferedProducerEvents.length) return;
		const pending = this.bufferedProducerEvents.splice(0);
		for (const data of pending) {
			// Skip if already have a consumer for this participant/kind
			const hasConsumer = Array.from(this.consumers.value.values()).some(
				(c) => c.participantId === data.participantId && c.kind === data.kind,
			);
			if (hasConsumer) continue;

			// Ensure participant exists with flags from paused
			let participant = this.participants.value.get(data.participantId);
			if (!participant) {
				participant = {
					user_id: data.participantId,
					user_name: data.participantId,
					initials: String(data.participantId).substring(0, 2).toUpperCase(),
					audio_enabled: false,
					video_enabled: false,
				};
			}
			if (data.kind === "audio") participant.audio_enabled = !data.paused;
			if (data.kind === "video") {
				const isScreen = !!data.isScreen || data.appData?.type === "screen";
				if (!isScreen) participant.video_enabled = !data.paused; // only set for real camera
			}
			this.participants.value.set(data.participantId, { ...participant });
			this.participants.value = new Map(this.participants.value);
			await nextTick();

			try {
				const consumer = await this.subscribeToNewProducer(
					data.producerId,
					data.participantId,
				);
				if (consumer?.track) {
					consumer.participantId = data.participantId;
					this.consumers.value.set(consumer.id, consumer);
					if (consumer.kind === "video") {
						await this.attachVideoStream(
							data.participantId,
							consumer,
							"buffered",
						);
					} else if (consumer.kind === "audio") {
						await this.attachAudioStream(data.participantId, consumer);
					}
				}
			} catch (e) {
				console.warn(
					"Failed to subscribe to buffered producer:",
					data,
					e?.message || e,
				);
			}
		}
	}

	/**
	 * Ensure all known consumers are attached to their DOM elements
	 */
	async reconcileAllAttachments() {
		// Build index of consumers by participant and kind
		const byParticipant = new Map();
		for (const consumer of this.consumers.value.values()) {
			if (!consumer.participantId) continue;
			const entry = byParticipant.get(consumer.participantId) || {};
			entry[consumer.kind] = consumer;
			byParticipant.set(consumer.participantId, entry);
		}

		for (const [participantId, kinds] of byParticipant.entries()) {
			// Skip local user
			if (
				participantId ===
				(this.currentUser &&
				typeof this.currentUser === "object" &&
				"value" in this.currentUser
					? this.currentUser.value?.user_id
					: null)
			)
				continue;

			// Ensure participant exists so a tile is rendered
			if (!this.participants.value.has(participantId)) {
				this.participants.value.set(participantId, {
					user_id: participantId,
					user_name: String(participantId),
					initials: String(participantId).substring(0, 2).toUpperCase(),
					audio_enabled: false,
					video_enabled: false,
				});
				this.participants.value = new Map(this.participants.value);
				await nextTick();
			}

			// Attach available streams
			if (kinds.video) {
				try {
					await this.attachVideoStream(participantId, kinds.video, "reconcile");
				} catch (e) {
					console.warn(
						"Attach video during reconcile failed:",
						participantId,
						e?.message || e,
					);
				}
			}
			if (kinds.audio) {
				try {
					await this.attachAudioStream(participantId, kinds.audio);
				} catch (e) {
					console.warn(
						"Attach audio during reconcile failed:",
						participantId,
						e?.message || e,
					);
				}
			}
		}
	}

	/**
	 * Request existing producers and attach them to video elements
	 */
	async requestExistingProducers() {
		try {
			const existingResult = await requestExistingProducers(this.meetingId);
			console.log("Requested existing producers successfully:", existingResult);

			if (existingResult?.subscriptions?.length) {
				console.log("Processing existing subscriptions...");
				for (const { consumer, producer } of existingResult.subscriptions) {
					if (!producer?.user_id) continue;

					// Determine if this existing producer represents a screen share BEFORE mutating participant flags
					const isScreen =
						!!producer.isScreen ||
						(producer.kind === "video" && producer.appData?.type === "screen");

					// Ensure participant exists with sensible defaults
					let participant = this.participants.value.get(producer.user_id);
					if (!participant) {
						participant = {
							user_id: producer.user_id,
							user_name: producer.user_id,
							avatar: producer.info?.avatar || null,
							initials: String(producer.user_id).substring(0, 2).toUpperCase(),
							audio_enabled: false,
							video_enabled: false,
						};
					}

					// Initialize flags from producer paused state. Only set video_enabled for NON-screen video producers.
					if (consumer.kind === "audio") {
						participant.audio_enabled = !producer.paused;
					} else if (consumer.kind === "video" && !isScreen) {
						participant.video_enabled = !producer.paused;
					} else if (isScreen) {
						// Ensure a screen-share-only participant (no camera) stays marked as video off
						participant.video_enabled =
							participant.video_enabled &&
							participant.video_enabled !== undefined
								? participant.video_enabled
								: false;
					}

					// Save participant and force reactivity
					this.participants.value.set(producer.user_id, { ...participant });
					this.participants.value = new Map(this.participants.value);

					// Wait a tick so UI renders the remote tile and sets ref
					await nextTick();

					// Track consumer with participant mapping for later controls
					try {
						consumer.participantId = producer.user_id;
						this.consumers.value.set(consumer.id, consumer);
					} catch (_) {}

					// Attach streams
					consumer.isScreen = isScreen;
					if (consumer.kind === "video" && isScreen) {
						// Track screen share producer so UI logic can locate it & fire handler
						this.screenShareProducers.set(producer.id, {
							participantId: producer.user_id,
						});
						if (this.eventHandlers.onScreenShareProducerAdded) {
							try {
								this.eventHandlers.onScreenShareProducerAdded({
									participantId: producer.user_id,
									producerId: producer.id,
									consumerId: consumer.id,
									consumer,
								});
							} catch (e) {
								console.warn(
									"Failed invoking onScreenShareProducerAdded for existing producer",
									e,
								);
							}
						}
					}
					if (consumer.kind === "video") {
						if (!isScreen) {
							await this.attachVideoStream(
								producer.user_id,
								consumer,
								"existing",
							);
						}
					} else if (consumer.kind === "audio") {
						await this.attachAudioStream(producer.user_id, consumer);
					}
				}

				// Final guard: ensure participants without a non-screen video consumer have video_enabled=false
				try {
					const cameraConsumersByParticipant = new Set(
						Array.from(this.consumers.value.values())
							.filter((c) => c.kind === "video" && c.isScreen !== true)
							.map((c) => c.participantId),
					);
					for (const [pid, participant] of this.participants.value.entries()) {
						if (!cameraConsumersByParticipant.has(pid)) {
							if (participant.video_enabled) {
								participant.video_enabled = false;
								this.participants.value.set(pid, { ...participant });
							}
						}
					}
					this.participants.value = new Map(this.participants.value);
				} catch (e) {
					console.warn("Camera consumer guard failed:", e?.message || e);
				}
			}

			return existingResult;
		} catch (error) {
			console.warn("Failed to request existing producers:", error);
			return null;
		}
	}

	/**
	 * Analyze video element to detect black/empty streams
	 */

	/**
	 * Find video element for a participant with comprehensive search
	 */
	async findVideoElement(participantId, maxAttempts = 10) {
		for (let attempt = 1; attempt <= maxAttempts; attempt++) {
			// 1) Check map first
			const remoteVideo = this.remoteVideos.value.get(participantId);
			if (remoteVideo && remoteVideo instanceof HTMLVideoElement)
				return remoteVideo;

			// 2) Try attribute-based selectors which are safe for arbitrary IDs
			try {
				const attrSel = `video[data-participant-id="${participantId}"]`;
				const byData = document.querySelector(attrSel);
				if (byData && byData instanceof HTMLVideoElement) {
					this.remoteVideos.value.set(participantId, byData);
					return byData;
				}
				const byParticipantAttr = document.querySelector(
					`[participant-id="${participantId}"] video`,
				);
				if (
					byParticipantAttr &&
					byParticipantAttr instanceof HTMLVideoElement
				) {
					this.remoteVideos.value.set(participantId, byParticipantAttr);
					return byParticipantAttr;
				}
				const byVideoAttr = document.querySelector(
					`video[participant-id="${participantId}"]`,
				);
				if (byVideoAttr && byVideoAttr instanceof HTMLVideoElement) {
					this.remoteVideos.value.set(participantId, byVideoAttr);
					return byVideoAttr;
				}
			} catch (e) {
				// Some browsers may throw if participantId contains unexpected characters in selector;
				// fall back to scanning all video elements below.
			}

			// 3) Fallback: scan all video elements and compare attributes directly
			const allVideos = document.querySelectorAll("video");
			for (const v of allVideos) {
				if (
					v.dataset?.participantId === participantId ||
					v.getAttribute("participant-id") === participantId ||
					v.id === `remote-video-${participantId}`
				) {
					this.remoteVideos.value.set(participantId, v);
					return v;
				}
			}

			// Log current state for debugging only every 10 attempts or at the end
			if (attempt % 10 === 0 || attempt === maxAttempts) {
				console.warn(
					`⚠️ Video element search status after ${attempt} attempts for ${participantId}`,
				);
			}

			if (attempt < maxAttempts) {
				await new Promise((resolve) => setTimeout(resolve, 100));
			}
		}

		console.error(
			`❌ Could not find video element for participant ${participantId} after ${maxAttempts} attempts`,
		);
		return null;
	}

	// Attach combined audio/video stream to video element with debugging
	// This method creates a combined MediaStream with both audio and video tracks
	// for better browser compatibility and follows mediasoup best practices
	async attachVideoStream(userId, consumer, userType = "new") {
		try {
			// Check that we have a valid track
			if (!consumer.track) {
				throw new Error(`Consumer ${consumer.id} has no track`);
			}

			// If this is a screen share consumer, avoid applying camera-based pause/resume logic.
			if (consumer.isScreen) {
				try {
					const existingEl = this.remoteVideos.value.get(userId);
					if (existingEl?.srcObject) {
						// Ensure playback
						if (existingEl.paused) {
							existingEl.play().catch(() => {});
						}
					}
				} catch (_) {}
				return;
			}

			// Find audio consumer and the primary (non-screen) video consumer for this participant
			const audioConsumer = Array.from(this.consumers.value.values()).find(
				(c) => c.participantId === userId && c.kind === "audio",
			);
			const videoConsumer = Array.from(this.consumers.value.values()).find(
				(c) =>
					c.participantId === userId &&
					c.kind === "video" &&
					c.isScreen !== true,
			);

			// Respect participant state: pause/resume based on audio_enabled/video_enabled
			const participant = this.participants.value.get(userId) || {};
			const wantAudio = !!participant.audio_enabled;
			const wantVideo = !!participant.video_enabled;

			// Toggle audio consumer
			if (audioConsumer) {
				try {
					if (!audioConsumer.closed) {
						if (!wantAudio && !audioConsumer.paused)
							await audioConsumer.pause();
						if (wantAudio && audioConsumer.paused) await audioConsumer.resume();
					}
				} catch (resumeError) {
					if (!audioConsumer?.closed) {
						console.error(
							`Failed to toggle audio consumer for user ${userId}:`,
							resumeError,
						);
					}
				}
			}

			// Toggle video consumer
			if (videoConsumer) {
				try {
					if (!videoConsumer.closed) {
						if (!wantVideo && !videoConsumer.paused)
							await videoConsumer.pause();
						if (wantVideo && videoConsumer.paused) await videoConsumer.resume();
					}
				} catch (resumeError) {
					if (!videoConsumer?.closed) {
						console.error(
							`Failed to toggle video consumer for user ${userId}:`,
							resumeError,
						);
					}
				}
			}

			// Handle muted tracks (usually means the producer has muted their stream)
			if (videoConsumer?.track?.muted) {
				const participantRecord = this.participants.value.get(userId) || {};
				if (!participantRecord._lastVideoMuted) {
					console.log(
						`Video track is muted for user ${userId} - likely producer has muted their stream`,
					);
					participantRecord._lastVideoMuted = true;
					this.participants.value.set(userId, { ...participantRecord });
					this.participants.value = new Map(this.participants.value);
				}

				const handleTrackUnmute = () => {
					const videoElement = this.remoteVideos.value.get(userId);
					if (videoElement?.srcObject) {
						videoElement
							.play()
							.catch((e) =>
								console.warn("Play after unmute failed:", e?.message || e),
							);
					}
					try {
						const pr = this.participants.value.get(userId) || {};
						pr._lastVideoMuted = false;
						this.participants.value.set(userId, { ...pr });
						this.participants.value = new Map(this.participants.value);
					} catch (_) {}
				};

				videoConsumer.track.addEventListener("unmute", handleTrackUnmute, {
					once: true,
				});
			}

			const videoElement = await this.findVideoElement(userId);

			if (videoElement) {
				// Create combined stream with both audio and video tracks
				const tracks = [];
				if (audioConsumer?.track) {
					tracks.push(audioConsumer.track);
				}
				if (videoConsumer?.track) {
					tracks.push(videoConsumer.track);
				}

				if (tracks.length === 0) {
					throw new Error(`No valid tracks found for user ${userId}`);
				}

				const stream = new MediaStream(tracks);

				// Set initial video element attributes based on video track state
				const videoTrack = videoConsumer?.track;
				if (videoTrack?.muted) {
					videoElement.setAttribute(
						"title",
						`User ${userId} has muted their video`,
					);
					console.log(`🔇 Setting muted visual indicators for user ${userId}`);
				} else if (videoTrack) {
					videoElement.removeAttribute("title");
					console.log(`📹 Video should be visible for user ${userId}`);
				}

				// Monitor video track mute/unmute events for visual updates
				if (videoTrack) {
					videoTrack.addEventListener("unmute", () => {
						console.log(
							`🔊 Video track unmuted for user ${userId} - updating visual indicators`,
						);
						videoElement.removeAttribute("title");
					});

					videoTrack.addEventListener("mute", () => {
						console.log(
							`🔇 Video track muted for user ${userId} - updating visual indicators`,
						);
						videoElement.setAttribute(
							"title",
							`User ${userId} has muted their video`,
						);
					});
				}

				// Attach stream to video element
				videoElement.srcObject = stream;

				// Save combined stream on participant for debugging/inspection and possible reuse
				try {
					const p = this.participants.value.get(userId) || {};
					p.videoStream = stream;
					this.participants.value.set(userId, { ...p });
					this.participants.value = new Map(this.participants.value);
				} catch (_) {}

				// Provide feedback based on video track state
				if (videoTrack?.muted) {
					console.log(
						`🔇 Attached combined stream with muted video for user ${userId} - waiting for producer to unmute`,
					);
					// Even muted streams should be attached so they're ready when unmuted
				} else if (videoTrack) {
					console.log(
						`📹 Attached combined stream with active video for user ${userId}`,
					);
				} else {
					console.log(
						`🎵 Attached audio-only stream for user ${userId} - no video track available`,
					);
				}

				try {
					await this.playVideoStream(videoElement, stream, userId);
				} catch (videoError) {
					console.warn(
						`⚠️ Standard video play failed, trying direct play method: ${videoError.message}`,
					);

					// Fallback to direct play method
					const directPlaySuccess = await this.playVideoStreamDirect(
						videoElement,
						stream,
						userId,
					);
					if (!directPlaySuccess) {
						console.error(
							`❌ Both video play methods failed for user ${userId}`,
						);
						throw videoError; // Re-throw original error
					}
					console.log(`✅ Direct play method succeeded for user ${userId}`);
				}
			} else {
				console.error(
					`❌ Video element not found for ${userType} user ${userId}`,
				);
				console.error(
					`🔍 Available elements: ${Array.from(this.remoteVideos.value.keys()).join(", ")}`,
				);
				throw new Error(`Video element not found for user ${userId}`);
			}
		} catch (error) {
			console.error(
				`❌ Failed to attach video stream for user ${userId}:`,
				error,
			);
			throw error;
		}
	}

	/**
	 * Attach audio stream to existing video element or create audio-only playback
	 */
	async attachAudioStream(userId, audioConsumer) {
		try {
			console.log(`🎵 Attaching audio stream for user ${userId}`);

			// Respect participant state before resuming
			const participant = this.participants.value.get(userId) || {};
			let wantAudio = participant.audio_enabled;

			if (typeof wantAudio === "undefined") {
				wantAudio = !audioConsumer?.paused;
				participant.audio_enabled = wantAudio;
				this.participants.value.set(userId, participant);
				console.log(
					`🔍 Inferred initial audio preference for ${userId}: ${wantAudio ? "enabled" : "muted"}`,
				);
			}
			if (audioConsumer) {
				try {
					if (participant.audio_enabled === false && !audioConsumer.paused)
						await audioConsumer.pause();
					if (wantAudio && audioConsumer.paused) await audioConsumer.resume();
					if (wantAudio)
						console.log(`✅ Audio consumer active for user ${userId}`);
					else if (participant.audio_enabled === false)
						console.log(`⏸️ Audio consumer paused for user ${userId}`);
				} catch (resumeError) {
					console.error(
						`Failed to toggle audio consumer for user ${userId}:`,
						resumeError,
					);
				}
			}

			// Check if there's already a video element for this participant
			const videoElement = this.remoteVideos.value.get(userId);

			if (videoElement) {
				// If video element exists, update its stream to include audio
				const existingStream = videoElement.srcObject;

				if (existingStream) {
					// Add the new audio track to the existing MediaStream to avoid aborting playback
					const existingTracks = existingStream.getTracks();
					if (
						audioConsumer.track &&
						!existingTracks.find((t) => t.id === audioConsumer.track.id)
					) {
						existingStream.addTrack(audioConsumer.track);
					}
				} else {
					// No existing stream, create audio-only stream
					if (audioConsumer.track) {
						const audioStream = new MediaStream([audioConsumer.track]);
						videoElement.srcObject = audioStream;
					}
				}

				const currentUserId = this.currentUser?.value?.user_id;
				videoElement.muted = userId === currentUserId;

				// Start playback if currently paused
				if (videoElement.paused) {
					try {
						await videoElement.play();
					} catch (playError) {
						console.warn(
							`⚠️ Audio play failed for user ${userId}:`,
							playError.message,
						);
						// Add user interaction handler for autoplay restrictions
						if (playError?.name === "NotAllowedError") {
							this.addUserInteractionHandler(videoElement, userId);
						}
					}
				}
			} else {
				// No video element found, create an audio-only element
				console.log(`🎵 Creating audio-only element for user ${userId}`);

				const audioElement = document.createElement("audio");
				audioElement.autoplay = true;
				audioElement.playsInline = true;
				audioElement.muted = false;

				if (audioConsumer.track) {
					const audioStream = new MediaStream([audioConsumer.track]);
					audioElement.srcObject = audioStream;

					try {
						await audioElement.play();
						console.log(`✅ Audio-only playback started for user ${userId}`);
					} catch (playError) {
						console.warn(
							`⚠️ Audio-only play failed for user ${userId}:`,
							playError.message,
						);
					}
				}
			}
		} catch (error) {
			console.error(
				`❌ Failed to attach audio stream for user ${userId}:`,
				error,
			);
			throw error;
		}
	}

	/**
	 * Play video stream with robust retry logic
	 */
	async playVideoStream(videoElement, stream, userId) {
		videoElement.srcObject = stream;
		videoElement.autoplay = true;
		videoElement.playsInline = true;
		videoElement.preload = "auto";
		// Mute only for local preview to avoid echo
		videoElement.muted =
			userId ===
			(this.currentUser &&
			typeof this.currentUser === "object" &&
			"value" in this.currentUser
				? this.currentUser.value?.user_id
				: null);

		// Try immediate playback without blocking waits
		try {
			await videoElement.play();
			return;
		} catch (err) {
			const tryPlay = async () => {
				try {
					await videoElement.play();
					cleanup();
				} catch (_) {}
			};

			const onLoadedMetadata = () => tryPlay();
			const onCanPlay = () => tryPlay();
			const onPlaying = () => cleanup();
			const onError = () => cleanup();

			const cleanup = () => {
				videoElement.removeEventListener("loadedmetadata", onLoadedMetadata);
				videoElement.removeEventListener("canplay", onCanPlay);
				videoElement.removeEventListener("playing", onPlaying);
				videoElement.removeEventListener("error", onError);
			};

			videoElement.addEventListener("loadedmetadata", onLoadedMetadata, {
				once: true,
			});
			videoElement.addEventListener("canplay", onCanPlay, { once: true });
			videoElement.addEventListener("playing", onPlaying, { once: true });
			videoElement.addEventListener("error", onError, { once: true });

			// If autoplay is blocked, prepare user interaction fallback
			if (err?.name === "NotAllowedError") {
				this.addUserInteractionHandler(videoElement, userId);
			}
		}
	}

	/**
	 * Alternative video playing method that skips metadata waiting
	 */
	async playVideoStreamDirect(videoElement, stream, userId) {
		try {
			// Set the stream
			videoElement.srcObject = stream;
			// Only mute if this is the local user to prevent echo, otherwise allow audio
			videoElement.muted =
				userId ===
				(this.currentUser &&
				typeof this.currentUser === "object" &&
				"value" in this.currentUser
					? this.currentUser.value?.user_id
					: null);
			videoElement.playsInline = true;

			// Try to play immediately without waiting for metadata
			await videoElement.play();

			return true;
		} catch (playError) {
			console.warn(
				`⚠️ Direct video play failed for user ${userId}:`,
				playError.message,
			);

			if (playError.name === "NotAllowedError") {
				console.log(
					`💡 User interaction required for direct video playback for ${userId}`,
				);
				this.addUserInteractionHandler(videoElement, userId);
				return true; // Consider this successful as we've set up interaction handler
			}

			return false;
		}
	}

	/**
	 * Add user interaction handler for autoplay restrictions
	 */
	addUserInteractionHandler(videoElement, userId) {
		const playOnInteraction = async () => {
			try {
				await videoElement.play();
				console.log(
					`Video started playing after user interaction for ${userId}`,
				);
				document.removeEventListener("click", playOnInteraction);
				document.removeEventListener("touchstart", playOnInteraction);
			} catch (e) {
				console.warn("Still failed to play video:", e.message);
			}
		};

		document.addEventListener("click", playOnInteraction, { once: true });
		document.addEventListener("touchstart", playOnInteraction, { once: true });
	}

	/**
	 * Subscribe to a new producer with enhanced validation
	 */
	async subscribeToNewProducer(producerId, participantId) {
		try {
			// Import the enhanced consumer creation function
			const { createValidatedConsumer } = await import(
				"../mediasoup-client.js"
			);

			// Create the consumer with built-in validation
			const consumer = await createValidatedConsumer(
				this.meetingId,
				producerId,
			);

			if (consumer) {
				// Add participant reference for easier tracking
				consumer.participantId = participantId;

				return consumer;
			}
			console.error(
				`❌ No consumer returned from createValidatedConsumer for producer ${producerId}`,
			);
			throw new Error(
				`Failed to create validated consumer for producer ${producerId}`,
			);
		} catch (error) {
			console.error(`❌ Error subscribing to producer ${producerId}: ${error}`);
			throw error;
		}
	} /**
	 * Setup SFU event handlers
	 */
	setupSFUEventHandlers() {
		console.log("🔧 Setting up SFU event handlers for direct communication");

		// Participant management
		const ensureRefs = () => {
			if (
				!this.currentUser ||
				typeof this.currentUser !== "object" ||
				!("value" in this.currentUser)
			) {
				this.currentUser = { value: null };
			}
			if (
				!this.participants ||
				typeof this.participants !== "object" ||
				!("value" in this.participants)
			) {
				this.participants = { value: new Map() };
			}
			if (
				!this.consumers ||
				typeof this.consumers !== "object" ||
				!("value" in this.consumers)
			) {
				this.consumers = { value: new Map() };
			}
			if (
				!this.remoteVideos ||
				typeof this.remoteVideos !== "object" ||
				!("value" in this.remoteVideos)
			) {
				this.remoteVideos = { value: new Map() };
			}
		};

		this.sfuClient.on("participant_joined", (data) => {
			ensureRefs();
			console.log("👥 Participant joined via SFU:", data);
			const participant = {
				user_id: data.participantId,
				user_name: data.userData?.name || data.participantId,
				avatar: data.userData?.avatar || null,
				initials: (data.userData?.name || data.participantId)
					.split(" ")
					.map((n) => n[0])
					.join("")
					.toUpperCase()
					.slice(0, 2),
				audio_enabled: undefined,
				video_enabled: undefined,
			};
			console.log("👥 Participant joined:", participant);

			this.participants.value.set(data.participantId, participant);

			// Notify parent component
			if (this.eventHandlers.onParticipantJoined) {
				this.eventHandlers.onParticipantJoined(participant);
			}
		});

		this.sfuClient.on("participant_left", (data) => {
			ensureRefs();
			// Avoid dereferencing possibly null refs
			const hasParticipantsRef = !!this.participants?.value;
			console.log(
				"👋 Participant left via SFU:",
				data,
				hasParticipantsRef ? this.participants.value : null,
			);

			// Remove participant from participants map
			this.participants?.value?.delete(data.participantId);

			// Clean up consumers for this participant (check both appData.userId and our participantId tag)
			for (const [consumerId, consumer] of this.consumers?.value?.entries?.() ||
				[]) {
				if (
					consumer.appData?.userId === data.participantId ||
					consumer.participantId === data.participantId
				) {
					try {
						consumer.close();
					} catch (_) {}
					this.consumers?.value?.delete(consumerId);
				}
			}

			// Clean up remote video element if present
			const videoEl = this.remoteVideos?.value?.get?.(data.participantId);
			if (videoEl) {
				try {
					for (const track of videoEl.srcObject?.getTracks?.() || []) {
						track.stop();
					}
					videoEl.srcObject = null;
				} catch (_) {}
				this.remoteVideos?.value?.delete?.(data.participantId);
			}

			// Notify parent component
			if (this.eventHandlers.onParticipantLeft) {
				this.eventHandlers.onParticipantLeft(data);
			}

			// Clear any screen share producers / consumers owned by this participant
			try {
				const toRemove = [];
				for (const [pid, meta] of this.screenShareProducers.entries()) {
					if (meta.participantId === data.participantId) toRemove.push(pid);
				}
				for (const pid of toRemove) {
					this.screenShareProducers.delete(pid);
					if (this.eventHandlers.onScreenShareProducerRemoved) {
						this.eventHandlers.onScreenShareProducerRemoved({
							participantId: data.participantId,
							producerId: pid,
						});
					}
				}
			} catch (e) {
				console.warn(
					"Failed to cleanup screen share state on participant_left",
					e,
				);
			}
		});

		// Media events
		this.sfuClient.on("producer_created", async (data) => {
			ensureRefs();
			console.log("🎥 New producer available via SFU:", data);

			const isScreen =
				!!data.isScreen ||
				(data.kind === "video" && data.appData?.type === "screen");
			if (isScreen) {
				this.screenShareProducers.set(data.producerId, {
					participantId: data.participantId,
				});
			}

			if (
				data.producerId &&
				data.participantId !==
					(this.currentUser &&
					typeof this.currentUser === "object" &&
					"value" in this.currentUser
						? this.currentUser.value?.user_id
						: null)
			) {
				try {
					if (this.initialSyncInProgress) {
						this.bufferedProducerEvents.push(data);
						return;
					}

					// Remove existing consumer of same media kind ONLY if both are screen shares or both are regular camera feeds.
					// This allows concurrent camera (video) + screen share (also video kind) for a participant.
					for (const [consumerId, consumer] of this.consumers.value.entries()) {
						if (consumer.participantId !== data.participantId) continue;
						if (consumer.kind !== data.kind) continue;
						const consumerIsScreen = consumer.isScreen;
						if (consumerIsScreen !== isScreen) {
							continue;
						}
						try {
							consumer.close();
						} catch (_) {}
						this.consumers.value.delete(consumerId);
					}

					// Ensure participant exists
					if (!this.participants.value.has(data.participantId)) {
						const participant = {
							user_id: data.participantId,
							user_name: data.participantId,
							avatar: data.userData?.avatar || null,
							initials: data.participantId.substring(0, 2).toUpperCase(),
							audio_enabled: false,
							video_enabled: false,
						};
						if (data.kind === "audio")
							participant.audio_enabled = data.paused !== true;
						if (data.kind === "video" && !isScreen)
							participant.video_enabled = data.paused !== true;
						this.participants.value.set(data.participantId, participant);
						this.participants.value = new Map(this.participants.value);
						await nextTick();
						await new Promise((resolve) => setTimeout(resolve, 200));
					} else {
						const existing = this.participants.value.get(data.participantId);
						if (!existing.avatar && data.userData?.avatar)
							existing.avatar = data.userData.avatar;
						if (typeof existing.audio_enabled === "undefined")
							existing.audio_enabled = false;
						if (typeof existing.video_enabled === "undefined")
							existing.video_enabled = false;
						if (data.kind === "audio")
							existing.audio_enabled = data.paused !== true;
						if (data.kind === "video" && !isScreen) {
							existing.video_enabled = data.paused !== true;
						}
						this.participants.value.set(data.participantId, { ...existing });
						this.participants.value = new Map(this.participants.value);
					}

					const consumer = await this.subscribeToNewProducer(
						data.producerId,
						data.participantId,
					);

					if (consumer?.track) {
						consumer.participantId = data.participantId;
						consumer.isScreen = !!isScreen;
						this.consumers.value.set(consumer.id, consumer);

						if (consumer.kind === "video") {
							if (isScreen) {
								if (this.eventHandlers.onScreenShareProducerAdded) {
									console.log(
										"🧩 Invoking onScreenShareProducerAdded handler",
										{
											participantId: data.participantId,
											producerId: data.producerId,
											consumerId: consumer.id,
											trackId: consumer.track?.id,
										},
									);
									this.eventHandlers.onScreenShareProducerAdded({
										participantId: data.participantId,
										producerId: data.producerId,
										consumerId: consumer.id,
										consumer,
									});
								}

								const cameraConsumer = Array.from(
									this.consumers.value.values(),
								).find(
									(c) =>
										c.participantId === data.participantId &&
										c.kind === "video" &&
										c.isScreen !== true,
								);
								if (cameraConsumer) {
									const videoEl = this.remoteVideos.value.get(
										data.participantId,
									);
									if (
										videoEl &&
										(!videoEl.srcObject ||
											!videoEl.srcObject
												.getVideoTracks()
												.some((t) => t.id === cameraConsumer.track?.id))
									) {
										console.log(
											"♻️ Re-attaching camera stream after screen share start for",
											data.participantId,
										);
										try {
											await this.attachVideoStream(
												data.participantId,
												cameraConsumer,
												"re-attach",
											);
										} catch (e) {
											console.warn("Failed to re-attach camera stream", e);
										}
									}
								}
							} else {
								await this.attachVideoStream(
									data.participantId,
									consumer,
									"new",
								);
							}
						} else if (consumer.kind === "audio") {
							await this.attachAudioStream(data.participantId, consumer);
						}

						if (this.eventHandlers.onConsumerCreated) {
							this.eventHandlers.onConsumerCreated(consumer, data);
						}
					} else {
						console.warn(
							`⚠️ No consumer or track created for producer ${data.producerId}`,
						);
					}
				} catch (error) {
					console.error(
						`❌ Failed to subscribe to producer ${data.producerId}:`,
						error,
					);
					if (this.eventHandlers.onSubscriptionError) {
						this.eventHandlers.onSubscriptionError(error, data);
					}
				}
			}
		});

		this.sfuClient.on("producer_closed", (data) => {
			ensureRefs();
			console.log("❌ Producer closed via SFU:", data);
			if (data.isScreen) {
				// Remove from screen share tracking
				for (const [pid, meta] of this.screenShareProducers.entries()) {
					if (pid === data.producerId) {
						this.screenShareProducers.delete(pid);
						if (this.eventHandlers.onScreenShareProducerRemoved) {
							this.eventHandlers.onScreenShareProducerRemoved({
								participantId: data.participantId,
								producerId: data.producerId,
							});
						}
						break;
					}
				}
			}
			// Find and close related consumers
			for (const [consumerId, consumer] of this.consumers.value.entries()) {
				if (consumer.producerId === data.producerId) {
					consumer.close();
					this.consumers.value.delete(consumerId);
				}
			}

			// Notify parent component
			if (this.eventHandlers.onProducerClosed) {
				this.eventHandlers.onProducerClosed(data);
			}
		});

		// Media control events
		this.sfuClient.on("media_control_update", async (data) => {
			ensureRefs();
			const consumersRef = this.consumers;
			const participantsRef = this.participants;
			const currentUserRef = this.currentUser;
			const remoteVideosRef = this.remoteVideos;

			console.log("🎛️ Media control update via SFU:", data);
			// Ignore self updates
			if (data.participantId === currentUserRef.value?.user_id) return;

			// Safely get or create participant
			let participant = participantsRef.value.get(data.participantId);
			if (!participant) {
				participant = {
					user_id: data.participantId,
					user_name: data.participantId,
					initials: String(data.participantId).substring(0, 2).toUpperCase(),
					audio_enabled: false,
					video_enabled: false,
				};
				participantsRef.value.set(data.participantId, participant);
			}

			try {
				if (data.action === "mute" || data.action === "unmute") {
					participant.audio_enabled = data.action === "unmute";

					for (const [consumerId, consumer] of consumersRef.value.entries()) {
						if (
							consumer.participantId === data.participantId &&
							consumer.kind === "audio"
						) {
							if (data.action === "mute") {
								try {
									await consumer.pause();
								} catch (_) {}
								// soft-pause: keep the consumer client-side so resume can happen locally without re-subscribing
								consumer._softPaused = true;
							} else {
								try {
									consumer._softPaused = false;
								} catch (_) {}
								try {
									await consumer.resume();
								} catch (_) {}
								try {
									await this.attachAudioStream(data.participantId, consumer);
								} catch (e) {
									console.warn(
										"Failed to resume/attach audio consumer on unmute:",
										e,
									);
								}
							}
						}
					}
				} else if (data.action === "video_off" || data.action === "video_on") {
					// Only apply camera state if there's a non-screen video consumer present
					const hasCameraConsumer = Array.from(
						consumersRef.value.values(),
					).some(
						(c) =>
							c.participantId === data.participantId &&
							c.kind === "video" &&
							c.isScreen !== true,
					);
					if (hasCameraConsumer) {
						participant.video_enabled = data.action === "video_on";
					} else {
						// Ignore video_on for screen-share-only case; ensure remains false on video_off
						if (data.action === "video_off") participant.video_enabled = false;
					}

					for (const [consumerId, consumer] of consumersRef.value.entries()) {
						if (
							consumer.participantId === data.participantId &&
							consumer.kind === "video"
						) {
							if (consumer.isScreen) {
								// Keep screen share always resumed regardless of camera toggles
								if (consumer.paused) {
									try {
										await consumer.resume();
										console.log(
											"🖥️ Ensured screen share consumer stays active on camera toggle",
											{ participantId: data.participantId, consumerId },
										);
									} catch (_) {}
								}
								continue; // skip camera pause/resume logic
							}
							if (!hasCameraConsumer) continue; // no camera to toggle
							if (data.action === "video_off") {
								try {
									await consumer.pause();
								} catch (_) {}
								consumer._softPaused = true;
							} else if (data.action === "video_on") {
								try {
									consumer._softPaused = false;
								} catch (_) {}
								try {
									await consumer.resume();
								} catch (_) {}
								try {
									await this.attachVideoStream(
										data.participantId,
										consumer,
										"reattach",
									);
								} catch (e) {
									console.warn(
										"Failed to re-attach/resume video consumer on video_on:",
										e,
									);
								}
							}
						}
					}
				}

				// Force Vue reactivity for participant map
				participantsRef.value.set(data.participantId, { ...participant });
				participantsRef.value = new Map(participantsRef.value);
			} catch (err) {
				console.warn("media_control_update handling error:", err);
			}

			if (this.eventHandlers.onMediaControlUpdate) {
				this.eventHandlers.onMediaControlUpdate(data, participant);
			}
		});

		// Screen sharing events
		this.sfuClient.on("screen_share_started", (data) => {
			ensureRefs();
			console.log("🖥️ Screen share started via SFU:", data);
			if (this.eventHandlers.onScreenShareStarted) {
				this.eventHandlers.onScreenShareStarted(data);
			}
		});

		this.sfuClient.on("screen_share_stopped", (data) => {
			ensureRefs();
			console.log("🖥️ Screen share stopped via SFU:", data);
			if (this.eventHandlers.onScreenShareStopped) {
				this.eventHandlers.onScreenShareStopped(data);
			}
		});
	}

	/**
	 * Disconnect from SFU
	 */
	async disconnect() {
		try {
			if (this.sfuClient && this.isConnected) {
				this.sfuClient.disconnect();
				console.log("✅ Disconnected from SFU");
			}
			this.isConnected = false;
		} catch (error) {
			console.error("❌ Error disconnecting from SFU:", error);
		}
	}

	/**
	 * Clean up all resources
	 */
	cleanup() {
		// Clean up consumers
		if (this.consumers) {
			for (const [consumerId, consumer] of this.consumers.value.entries()) {
				consumer.close();
			}
			this.consumers.value.clear();
		}

		// Disconnect from SFU
		this.disconnect();

		// Reset state
		this.sfuClient = null;
		this.meetingId = null;
		this.currentUser = { value: null };
		this.participants = { value: new Map() };
		this.consumers = { value: new Map() };
		this.remoteVideos = { value: new Map() };
		this.eventHandlers = {};
		this.isConnected = false;
	}
}

// Export singleton instance
let sfuManagerInstance = null;

export function getSFUMeetingManager() {
	if (!sfuManagerInstance) {
		sfuManagerInstance = new SFUMeetingManager();
	}
	return sfuManagerInstance;
}

export function resetSFUMeetingManager() {
	if (sfuManagerInstance) {
		sfuManagerInstance.cleanup();
		sfuManagerInstance = null;
	}
}
