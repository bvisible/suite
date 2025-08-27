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
		this.currentUser = null;
		this.participants = null;
		this.consumers = null;
		this.remoteVideos = null;
		this.eventHandlers = {};
		this.isConnected = false;
		this.initialSyncInProgress = false;
		this.bufferedProducerEvents = [];
	}

	/**
	 * Initialize the SFU manager with required dependencies
	 */
	initialize(options) {
		this.meetingId = options.meetingId;
		this.currentUser = options.currentUser;
		this.participants = options.participants ||
			this.participants || { value: new Map() };
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
						if (p.user_id && p.user_id !== this.currentUser.value?.user_id) {
							const existing = this.participants.value.get(p.user_id);
							if (!existing) {
								this.participants.value.set(p.user_id, {
									user_id: p.user_id,
									user_name: p.info?.name || p.user_id,
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
									video_enabled:
										typeof p.info?.video_enabled === "boolean"
											? p.info.video_enabled
											: false,
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
			if (data.kind === "video") participant.video_enabled = !data.paused;
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
			if (participantId === this.currentUser.value?.user_id) continue;

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

					// Ensure participant exists with sensible defaults
					let participant = this.participants.value.get(producer.user_id);
					if (!participant) {
						participant = {
							user_id: producer.user_id,
							user_name: producer.user_id,
							initials: String(producer.user_id).substring(0, 2).toUpperCase(),
							audio_enabled: false,
							video_enabled: false,
						};
					}

					// Initialize flags from producer paused state
					if (consumer.kind === "audio") {
						participant.audio_enabled = !producer.paused;
					} else if (consumer.kind === "video") {
						participant.video_enabled = !producer.paused;
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
					if (consumer.kind === "video") {
						await this.attachVideoStream(
							producer.user_id,
							consumer,
							"existing",
						);
					} else if (consumer.kind === "audio") {
						await this.attachAudioStream(producer.user_id, consumer);
					}
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
			// Search in remoteVideos Map
			const remoteVideo = this.remoteVideos.value.get(participantId);
			if (remoteVideo && remoteVideo instanceof HTMLVideoElement) {
				return remoteVideo;
			}

			// Search in DOM using multiple selectors
			const selectors = [
				`video[data-participant-id="${participantId}"]`,
				`.remote-video-${participantId}`,
				`#remote-video-${participantId}`,
				`[participant-id="${participantId}"] video`,
				`video[participant-id="${participantId}"]`,
				`.participant-${participantId} video`,
			];

			for (const selector of selectors) {
				const element = document.querySelector(selector);
				if (element) {
					// Update remoteVideos Map
					this.remoteVideos.value.set(participantId, element);
					return element;
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

			// Find both audio and video consumers for this participant
			const audioConsumer = Array.from(this.consumers.value.values()).find(
				(c) => c.participantId === userId && c.kind === "audio",
			);
			const videoConsumer = Array.from(this.consumers.value.values()).find(
				(c) => c.participantId === userId && c.kind === "video",
			);

			// Respect participant state: pause/resume based on audio_enabled/video_enabled
			const participant = this.participants.value.get(userId) || {};
			const wantAudio = participant.audio_enabled === true; // strict
			const wantVideo = participant.video_enabled === true; // strict

			// Toggle audio consumer
			if (audioConsumer) {
				try {
					if (!wantAudio && !audioConsumer.paused) await audioConsumer.pause();
					if (wantAudio && audioConsumer.paused) await audioConsumer.resume();
				} catch (resumeError) {
					console.error(
						`Failed to toggle audio consumer for user ${userId}:`,
						resumeError,
					);
				}
			}

			// Toggle video consumer
			if (videoConsumer) {
				try {
					if (!wantVideo && !videoConsumer.paused) await videoConsumer.pause();
					if (wantVideo && videoConsumer.paused) await videoConsumer.resume();
				} catch (resumeError) {
					console.error(
						`Failed to toggle video consumer for user ${userId}:`,
						resumeError,
					);
				}
			}

			// Handle muted tracks (usually means the producer has muted their stream)
			if (videoConsumer?.track?.muted) {
				console.log(
					`Video track is muted for user ${userId} - likely producer has muted their stream`,
				);

				// On unmute, simply attempt to play without detaching/reattaching the stream
				const handleTrackUnmute = () => {
					const videoElement = this.remoteVideos.value.get(userId);
					if (videoElement?.srcObject) {
						videoElement
							.play()
							.catch((e) =>
								console.warn("Play after unmute failed:", e?.message || e),
							);
					}
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

				console.log("📺 Stream details before attachment:", {
					streamId: stream.id,
					tracks: stream.getTracks().length,
					audioTracks: stream.getAudioTracks().length,
					videoTracks: stream.getVideoTracks().length,
					active: stream.active,
					trackStates: stream.getTracks().map((t) => ({
						id: t.id,
						kind: t.kind,
						readyState: t.readyState,
						enabled: t.enabled,
						muted: t.muted,
					})),
				});

				// Attach stream to video element
				videoElement.srcObject = stream;

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

				// Verify tracks in the combined stream
				const streamVideoTracks = stream.getVideoTracks();
				const streamAudioTracks = stream.getAudioTracks();

				if (streamVideoTracks.length > 0) {
					const streamVideoTrack = streamVideoTracks[0];
					console.log("🎞️ Video track verification: ", {
						id: streamVideoTrack.id,
						kind: streamVideoTrack.kind,
						enabled: streamVideoTrack.enabled,
						muted: streamVideoTrack.muted,
						readyState: streamVideoTrack.readyState,
						label: streamVideoTrack.label,
						sameAsConsumerTrack: streamVideoTrack === videoConsumer?.track,
					});
				} else {
					console.warn("⚠️ No video tracks found in created stream!");
				}

				if (streamAudioTracks.length > 0) {
					const streamAudioTrack = streamAudioTracks[0];
					console.log("🎵 Audio track verification: ", {
						id: streamAudioTrack.id,
						kind: streamAudioTrack.kind,
						enabled: streamAudioTrack.enabled,
						muted: streamAudioTrack.muted,
						readyState: streamAudioTrack.readyState,
						label: streamAudioTrack.label,
						sameAsConsumerTrack: streamAudioTrack === audioConsumer?.track,
					});
				} else {
					console.log("ℹ️ No audio tracks found in created stream");
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
			const wantAudio = participant.audio_enabled === true; // strict
			if (audioConsumer) {
				try {
					if (!wantAudio && !audioConsumer.paused) await audioConsumer.pause();
					if (wantAudio && audioConsumer.paused) await audioConsumer.resume();
					if (wantAudio)
						console.log(`✅ Audio consumer active for user ${userId}`);
					else console.log(`⏸️ Audio consumer paused for user ${userId}`);
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

				// Ensure the video element is not muted so we can hear audio when enabled
				videoElement.muted = !wantAudio;

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
		videoElement.muted = userId === this.currentUser.value?.user_id;

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
			videoElement.muted = userId === this.currentUser.value?.user_id;
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
		this.sfuClient.on("participant_joined", (data) => {
			console.log("👥 Participant joined via SFU:", data);
			const participant = {
				user_id: data.participantId,
				user_name: data.userData?.name || data.participantId,
				initials: (data.userData?.name || data.participantId)
					.split(" ")
					.map((n) => n[0])
					.join("")
					.toUpperCase()
					.slice(0, 2),
				audio_enabled: false,
				video_enabled: false,
			};
			console.log("👥 Participant joined:", participant);

			this.participants.value.set(data.participantId, participant);

			// Notify parent component
			if (this.eventHandlers.onParticipantJoined) {
				this.eventHandlers.onParticipantJoined(participant);
			}
		});

		this.sfuClient.on("participant_left", (data) => {
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
		});

		// Media events
		this.sfuClient.on("producer_created", async (data) => {
			console.log("🎥 New producer available via SFU:", data);

			if (
				data.producerId &&
				data.participantId !== this.currentUser.value?.user_id
			) {
				try {
					if (this.initialSyncInProgress) {
						this.bufferedProducerEvents.push(data);
						return;
					}

					// Always remove any existing consumer for this participant/kind
					for (const [consumerId, consumer] of this.consumers.value.entries()) {
						if (
							consumer.participantId === data.participantId &&
							consumer.kind === data.kind
						) {
							try {
								consumer.close();
							} catch (_) {}
							this.consumers.value.delete(consumerId);
						}
					}

					// Ensure participant exists
					if (!this.participants.value.has(data.participantId)) {
						const participant = {
							user_id: data.participantId,
							user_name: data.participantId,
							initials: data.participantId.substring(0, 2).toUpperCase(),
							audio_enabled: false,
							video_enabled: false,
						};
						if (data.kind === "audio")
							participant.audio_enabled = data.paused !== true;
						if (data.kind === "video")
							participant.video_enabled = data.paused !== true;
						this.participants.value.set(data.participantId, participant);
						this.participants.value = new Map(this.participants.value);
						await nextTick();
						await new Promise((resolve) => setTimeout(resolve, 200));
					} else {
						const existing = this.participants.value.get(data.participantId);
						if (typeof existing.audio_enabled === "undefined")
							existing.audio_enabled = false;
						if (typeof existing.video_enabled === "undefined")
							existing.video_enabled = false;
						if (data.kind === "audio")
							existing.audio_enabled = data.paused !== true;
						if (data.kind === "video")
							existing.video_enabled = data.paused !== true;
						this.participants.value.set(data.participantId, { ...existing });
						this.participants.value = new Map(this.participants.value);
					}

					const consumer = await this.subscribeToNewProducer(
						data.producerId,
						data.participantId,
					);

					if (consumer?.track) {
						consumer.participantId = data.participantId;
						this.consumers.value.set(consumer.id, consumer);

						if (consumer.kind === "video") {
							await this.attachVideoStream(data.participantId, consumer, "new");
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
			console.log("❌ Producer closed via SFU:", data);
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
			console.log("🎛️ Media control update via SFU:", data);
			// Ignore self updates to avoid duplicating local user as a remote participant
			if (data.participantId === this.currentUser.value?.user_id) {
				return;
			}
			let participant = this.participants.value.get(data.participantId);
			// If participant not present yet (race), create a minimal placeholder
			if (!participant) {
				participant = {
					user_id: data.participantId,
					user_name: data.participantId,
					initials: String(data.participantId).substring(0, 2).toUpperCase(),
					audio_enabled: false,
					video_enabled: false,
				};
				this.participants.value.set(data.participantId, participant);
			}
			if (participant) {
				try {
					if (data.action === "mute" || data.action === "unmute") {
						participant.audio_enabled = data.action === "unmute";
						for (const [
							consumerId,
							consumer,
						] of this.consumers.value.entries()) {
							if (
								consumer.participantId === data.participantId &&
								consumer.kind === "audio"
							) {
								if (data.action === "mute") {
									try {
										consumer.close();
									} catch (_) {}
									this.consumers.value.delete(consumerId);
								}
							}
						}
					} else if (
						data.action === "video_off" ||
						data.action === "video_on"
					) {
						participant.video_enabled = data.action === "video_on";
						for (const [
							consumerId,
							consumer,
						] of this.consumers.value.entries()) {
							if (
								consumer.participantId === data.participantId &&
								consumer.kind === "video"
							) {
								if (data.action === "video_off") {
									try {
										consumer.close();
									} catch (_) {}
									this.consumers.value.delete(consumerId);
								}
							}
						}
					}

					// Force Vue to notice participant flag changes when using Map in a ref
					this.participants.value.set(data.participantId, { ...participant });
					this.participants.value = new Map(this.participants.value);
				} catch (err) {
					console.warn("media_control_update handling error:", err);
				}

				// Notify parent component
				if (this.eventHandlers.onMediaControlUpdate) {
					this.eventHandlers.onMediaControlUpdate(data, participant);
				}
			}
		});

		// Screen sharing events
		this.sfuClient.on("screen_share_started", (data) => {
			console.log("🖥️ Screen share started via SFU:", data);
			if (this.eventHandlers.onScreenShareStarted) {
				this.eventHandlers.onScreenShareStarted(data);
			}
		});

		this.sfuClient.on("screen_share_stopped", (data) => {
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
		this.currentUser = null;
		this.participants = null;
		this.consumers = null;
		this.remoteVideos = null;
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
