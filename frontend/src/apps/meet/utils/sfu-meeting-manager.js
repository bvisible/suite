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
	}

	/**
	 * Initialize the SFU manager with required dependencies
	 */
	initialize(options) {
		this.meetingId = options.meetingId;
		this.currentUser = options.currentUser;
		this.participants = options.participants;
		this.consumers = options.consumers;
		this.remoteVideos = options.remoteVideos;
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
			console.log("✅ Connected to SFU directly");

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
			if (localStream && shouldPublishVideo) {
				results.videoProducer = await publishVideo(this.meetingId, localStream);
			}

			if (localStream && shouldPublishAudio) {
				results.audioProducer = await publishAudio(this.meetingId, localStream);
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
	async setupExistingParticipants(existingMembers) {
		try {
			console.log("👥 Setting up existing participants...");

			// Add existing participants to state
			if (existingMembers && existingMembers.length > 0) {
				console.log("Found existing members:", existingMembers);

				for (const member of existingMembers) {
					if (member.user !== this.currentUser.value?.name) {
						const participant = {
							user_id: member.user,
							user_name: member.full_name || member.user,
							initials: (member.full_name || member.user || "U")
								.split(" ")
								.map((n) => n[0])
								.join("")
								.toUpperCase()
								.slice(0, 2),
							audio_enabled: true,
							video_enabled: true,
						};
						this.participants.value.set(member.user, participant);
						console.log("Added existing participant:", participant);
					}
				}

				// Wait for DOM to update with new participants
				await nextTick();
				console.log("DOM updated with existing participants");
				await new Promise((resolve) => setTimeout(resolve, 100));
			}

			// Request existing producers from the SFU
			await this.requestExistingProducers();

			return true;
		} catch (error) {
			console.error("❌ Error setting up existing participants:", error);
			throw error;
		}
	}

	/**
	 * Request existing producers and attach them to video elements
	 */
	async requestExistingProducers() {
		try {
			const existingResult = await requestExistingProducers(this.meetingId);
			console.log("Requested existing producers successfully:", existingResult);

			if (existingResult?.subscriptions) {
				console.log("Processing existing subscriptions...");
				await nextTick();

				for (const { consumer, producer } of existingResult.subscriptions) {
					if (consumer.kind === "video" && producer.user_id) {
						await this.attachVideoStream(
							producer.user_id,
							consumer,
							"existing",
						);
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
	async analyzeVideoStream(participantId) {
		const videoElement = this.remoteVideos.value.get(participantId);
		if (!videoElement) {
			console.log(`❌ No video element found for participant ${participantId}`);
			return null;
		}

		const analysis = {
			participantId,
			timestamp: new Date().toISOString(),
			videoElement: {
				readyState: videoElement.readyState,
				networkState: videoElement.networkState,
				videoWidth: videoElement.videoWidth,
				videoHeight: videoElement.videoHeight,
				currentTime: videoElement.currentTime,
				duration: videoElement.duration,
				paused: videoElement.paused,
				ended: videoElement.ended,
				muted: videoElement.muted,
				hasStream: !!videoElement.srcObject,
				streamId: videoElement.srcObject?.id,
				streamActive: videoElement.srcObject?.active,
			},
			stream: null,
			track: null,
			consumer: null,
			pixelAnalysis: null,
		};

		// Analyze stream
		if (videoElement.srcObject) {
			const stream = videoElement.srcObject;
			const videoTracks = stream.getVideoTracks();

			analysis.stream = {
				id: stream.id,
				active: stream.active,
				videoTrackCount: videoTracks.length,
				tracks: videoTracks.map((track) => ({
					id: track.id,
					kind: track.kind,
					enabled: track.enabled,
					muted: track.muted,
					readyState: track.readyState,
					label: track.label,
					settings: track.getSettings?.() || null,
				})),
			};

			// Analyze the video track
			if (videoTracks.length > 0) {
				const track = videoTracks[0];
				analysis.track = {
					id: track.id,
					enabled: track.enabled,
					muted: track.muted,
					readyState: track.readyState,
					settings: track.getSettings?.() || null,
					capabilities: track.getCapabilities?.() || null,
				};
			}
		}

		// Find associated consumer
		for (const [consumerId, consumer] of this.consumers.value.entries()) {
			if (
				consumer.participantId === participantId &&
				consumer.kind === "video"
			) {
				analysis.consumer = {
					id: consumer.id,
					paused: consumer.paused,
					producerId: consumer.producerId,
					trackId: consumer.track?.id,
					trackMuted: consumer.track?.muted,
					trackEnabled: consumer.track?.enabled,
					trackReadyState: consumer.track?.readyState,
				};
				break;
			}
		}

		// Pixel analysis to detect black video
		if (
			videoElement.videoWidth > 0 &&
			videoElement.videoHeight > 0 &&
			videoElement.readyState >= 2
		) {
			analysis.pixelAnalysis = await this.analyzeVideoPixels(videoElement);
		}

		return analysis;
	}

	/**
	 * Analyze video pixels to detect black/empty frames
	 */
	async analyzeVideoPixels(videoElement) {
		try {
			// Create a canvas to capture video frame
			const canvas = document.createElement("canvas");
			const ctx = canvas.getContext("2d");

			canvas.width = Math.min(videoElement.videoWidth, 320); // Limit size for performance
			canvas.height = Math.min(videoElement.videoHeight, 240);

			// Draw current video frame to canvas
			ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

			// Get image data
			const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
			const pixels = imageData.data;

			let totalPixels = 0;
			let blackPixels = 0;
			let totalBrightness = 0;
			let colorVariance = 0;
			const rgbSums = { r: 0, g: 0, b: 0 };

			// Analyze pixels (RGBA format)
			for (let i = 0; i < pixels.length; i += 4) {
				const r = pixels[i];
				const g = pixels[i + 1];
				const b = pixels[i + 2];
				const a = pixels[i + 3]; // Alpha channel

				totalPixels++;

				// Calculate brightness (luminance)
				const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
				totalBrightness += brightness;

				// Count near-black pixels (threshold of 10 for very dark)
				if (brightness < 10 && a > 0) {
					blackPixels++;
				}

				// Sum RGB values
				rgbSums.r += r;
				rgbSums.g += g;
				rgbSums.b += b;
			}

			const avgBrightness = totalBrightness / totalPixels;
			const blackPercentage = (blackPixels / totalPixels) * 100;
			const avgColors = {
				r: rgbSums.r / totalPixels,
				g: rgbSums.g / totalPixels,
				b: rgbSums.b / totalPixels,
			};

			// Calculate color variance to detect uniform colors
			let varianceSum = 0;
			for (let i = 0; i < pixels.length; i += 4) {
				const r = pixels[i];
				const g = pixels[i + 1];
				const b = pixels[i + 2];
				const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
				varianceSum += brightness - avgBrightness ** 2;
			}
			colorVariance = varianceSum / totalPixels;

			const analysis = {
				dimensions: { width: canvas.width, height: canvas.height },
				totalPixels,
				avgBrightness: Math.round(avgBrightness),
				blackPixels,
				blackPercentage: Math.round(blackPercentage * 100) / 100,
				avgColors: {
					r: Math.round(avgColors.r),
					g: Math.round(avgColors.g),
					b: Math.round(avgColors.b),
				},
				colorVariance: Math.round(colorVariance),
				isLikelyBlack: blackPercentage > 95 || avgBrightness < 5,
				isLikelyEmpty: colorVariance < 10 && avgBrightness < 20,
				hasContent: avgBrightness > 30 && colorVariance > 50,
			};

			// Clean up canvas
			canvas.remove();

			return analysis;
		} catch (error) {
			console.warn(`⚠️ Failed to analyze video pixels: ${error}`);
			return {
				error: error.message,
				isLikelyBlack: false,
				isLikelyEmpty: false,
				hasContent: false,
			};
		}
	}

	/**
	 * Comprehensive video stream health check
	 */
	async checkVideoStreamHealth(participantId) {
		console.log(`🏥 Performing video stream health check for ${participantId}`);

		const analysis = await this.analyzeVideoStream(participantId);
		if (!analysis) return null;

		const issues = [];
		const suggestions = [];

		// Check for common issues
		if (!analysis.videoElement.hasStream) {
			issues.push("No stream attached to video element");
			suggestions.push("Check if consumer track is properly attached");
		}

		if (analysis.consumer?.paused) {
			issues.push("Consumer is paused");
			suggestions.push("Call consumer.resume() to start receiving media");
		}

		if (analysis.track?.muted) {
			issues.push("Video track is muted by producer");
			suggestions.push("Producer needs to unmute their video");
		}

		if (!analysis.track?.enabled) {
			issues.push("Video track is disabled");
			suggestions.push("Check track.enabled property");
		}

		if (analysis.track?.readyState === "ended") {
			issues.push("Video track has ended");
			suggestions.push("Track may have been stopped by producer");
		}

		if (analysis.videoElement.readyState < 2) {
			issues.push("Video element not ready (no metadata loaded)");
			suggestions.push("Wait for video metadata to load");
		}

		if (
			analysis.videoElement.videoWidth === 0 ||
			analysis.videoElement.videoHeight === 0
		) {
			issues.push("Video has no dimensions");
			suggestions.push("Check if video track has proper resolution");
		}

		if (analysis.pixelAnalysis?.isLikelyBlack) {
			issues.push("Video appears to be completely black");
			suggestions.push(
				"Producer may have camera issues or be in dark environment",
			);
		}

		if (analysis.pixelAnalysis?.isLikelyEmpty) {
			issues.push("Video appears to be empty/static");
			suggestions.push(
				"Producer may have paused their camera or have technical issues",
			);
		}

		const healthScore = Math.max(0, 100 - issues.length * 15);
		const isHealthy = healthScore > 70 && analysis.pixelAnalysis?.hasContent;

		const healthReport = {
			participantId,
			timestamp: new Date().toISOString(),
			isHealthy,
			healthScore,
			issues,
			suggestions,
			analysis,
		};

		return healthReport;
	}

	/**
	 * Check video stream health for all participants
	 */
	async checkAllVideoStreams() {
		const results = new Map();

		for (const participantId of this.remoteVideos.value.keys()) {
			try {
				const healthReport = await this.checkVideoStreamHealth(participantId);
				if (healthReport) {
					results.set(participantId, healthReport);
				}
			} catch (error) {
				console.error(
					`❌ Failed to check video stream for ${participantId}:`,
					error,
				);
				results.set(participantId, {
					participantId,
					error: error.message,
					isHealthy: false,
					healthScore: 0,
				});
			}
		}

		// Summary report
		const healthyCount = Array.from(results.values()).filter(
			(r) => r.isHealthy,
		).length;
		const totalCount = results.size;

		return results;
	}

	/**
	 * Find video element for a participant with comprehensive search
	 */
	async findVideoElement(participantId, maxAttempts = 30) {
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
				await new Promise((resolve) => setTimeout(resolve, 200)); // Wait 200ms between attempts
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

			// Resume all consumers for this participant
			const consumersToResume = [audioConsumer, videoConsumer].filter(
				(c) => c?.paused,
			);

			for (const consumerToResume of consumersToResume) {
				try {
					await consumerToResume.resume();
				} catch (resumeError) {
					console.error(
						`Failed to resume ${consumerToResume.kind} consumer for user ${userId}:`,
						resumeError,
					);
					throw resumeError; // This is critical, so throw the error
				}
			}

			// Handle muted tracks (usually means the producer has muted their stream)
			if (videoConsumer?.track?.muted) {
				console.log(
					`Video track is muted for user ${userId} - likely producer has muted their stream`,
				);

				// Set up a listener for when the producer unmutes
				const handleTrackUnmute = () => {
					console.log(
						`Video track unmuted for user ${userId} - producer enabled their stream`,
					);
					// Force video element to recognize the unmuted stream
					const videoElement = this.remoteVideos.value.get(userId);
					if (videoElement?.srcObject) {
						// Trigger a refresh by briefly removing and re-adding the stream
						const currentStream = videoElement.srcObject;
						videoElement.srcObject = null;
						setTimeout(() => {
							videoElement.srcObject = currentStream;
							videoElement
								.play()
								.catch((e) => console.warn("Play after unmute failed:", e));
						}, 10);
					}
				};

				videoConsumer.track.addEventListener("unmute", handleTrackUnmute, {
					once: true,
				});
			}

			// Use the new helper function to find video element
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
					console.log(
						"ℹ️ No audio tracks found in created stream (audio-only streams are handled separately)",
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

				// Run a health check after a short delay to allow video to stabilize
				setTimeout(async () => {
					try {
						const healthReport = await this.checkVideoStreamHealth(userId);
						if (healthReport && !healthReport.isHealthy) {
							console.warn(
								`⚠️ Video stream health issues detected for ${userId}:`,
								{
									healthScore: healthReport.healthScore,
									issues: healthReport.issues,
								},
							);
						}
					} catch (error) {
						console.warn(
							`⚠️ Failed to run health check for ${userId}:`,
							error.message,
						);
					}
				}, 2000); // Wait 2 seconds for video to stabilize
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
	 * Play video stream with robust retry logic
	 */
	async playVideoStream(videoElement, stream, userId) {
		// Log track details
		const videoTracks = stream.getVideoTracks();
		videoTracks.forEach((track, index) => {
			console.log(`📹 Video track ${index}:`, {
				id: track.id,
				kind: track.kind,
				enabled: track.enabled,
				muted: track.muted,
				readyState: track.readyState,
				label: track.label,
				settings: track.getSettings?.(),
			});
		});

		const playVideo = async () => {
			// Set the stream
			videoElement.srcObject = stream;
			videoElement.muted = true;
			videoElement.playsInline = true;

			// Wait for metadata and canplay
			await new Promise((resolve, reject) => {
				let resolved = false;
				const timeout = setTimeout(() => {
					if (!resolved) {
						console.error(
							`⏰ Timeout waiting for video to be ready for user ${userId}`,
						);
						reject(new Error("Timeout waiting for video to be ready"));
					}
				}, 8000); // Increase timeout to 8 seconds for better debugging

				const onReady = () => {
					if (!resolved) {
						resolved = true;
						clearTimeout(timeout);
						resolve();
					}
				};

				const onError = (error) => {
					console.error(`❌ Video element error for user ${userId}: ${error}`);
					console.error("📱 Video element error state:", {
						error: videoElement.error,
						readyState: videoElement.readyState,
						networkState: videoElement.networkState,
					});
					if (!resolved) {
						resolved = true;
						clearTimeout(timeout);
						reject(error);
					}
				};

				// Add event listeners
				videoElement.addEventListener("loadedmetadata", onReady, {
					once: true,
				});
				videoElement.addEventListener("canplay", onReady, { once: true });
				videoElement.addEventListener("error", onError, { once: true });

				// Check if already loaded
				if (videoElement.readyState >= 3) {
					onReady();
				}
			});

			// Add a short delay to ensure browser is ready
			await new Promise((r) => setTimeout(r, 50));

			// Try to play with retry logic
			let attempts = 0;
			while (attempts < 3) {
				try {
					await videoElement.play();
					return;
				} catch (playError) {
					attempts++;
					console.warn(
						`⚠️ Video play failed (attempt ${attempts}):`,
						playError.message,
					);

					if (playError.name === "AbortError" && attempts < 3) {
						await new Promise((r) => setTimeout(r, 150));
					} else if (playError.name === "NotAllowedError") {
						console.log(
							`💡 User interaction required for video playback for ${userId}`,
						);
						this.addUserInteractionHandler(videoElement, userId);
						break;
					} else {
						break;
					}
				}
			}
		};

		await playVideo();
	}

	/**
	 * Alternative video playing method that skips metadata waiting
	 */
	async playVideoStreamDirect(videoElement, stream, userId) {
		try {
			// Set the stream
			videoElement.srcObject = stream;
			videoElement.muted = true;
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
				audio_enabled: true,
				video_enabled: true,
			};
			this.participants.value.set(data.participantId, participant);

			// Notify parent component
			if (this.eventHandlers.onParticipantJoined) {
				this.eventHandlers.onParticipantJoined(participant);
			}
		});

		this.sfuClient.on("participant_left", (data) => {
			console.log("👋 Participant left via SFU:", data);
			this.participants.value.delete(data.participantId);

			// Clean up consumers for this participant
			for (const [consumerId, consumer] of this.consumers.value.entries()) {
				if (consumer.appData?.userId === data.participantId) {
					consumer.close();
					this.consumers.value.delete(consumerId);
				}
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
					// Ensure participant exists
					if (!this.participants.value.has(data.participantId)) {
						const participant = {
							user_id: data.participantId,
							user_name: data.participantId, // Will be updated when participant data is available
							initials: data.participantId.substring(0, 2).toUpperCase(),
							audio_enabled: true,
							video_enabled: true,
						};
						this.participants.value.set(data.participantId, participant);

						// Wait for DOM update
						await nextTick();
						await new Promise((resolve) => setTimeout(resolve, 200)); // Give more time for DOM
					}

					const consumer = await this.subscribeToNewProducer(
						data.producerId,
						data.participantId,
					);

					if (consumer?.track) {
						// Store consumer with participant info
						consumer.participantId = data.participantId;
						this.consumers.value.set(consumer.id, consumer);

						// Only attach video streams
						if (consumer.kind === "video") {
							await this.attachVideoStream(data.participantId, consumer, "new");
						}

						// Notify parent component
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

					// Notify parent component of error
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
		this.sfuClient.on("media_control_update", (data) => {
			console.log("🎛️ Media control update via SFU:", data);
			const participant = this.participants.value.get(data.participantId);
			if (participant) {
				if (data.action === "mute" || data.action === "unmute") {
					participant.audio_enabled = data.action === "unmute";
				} else if (data.action === "video_off" || data.action === "video_on") {
					participant.video_enabled = data.action === "video_on";
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
