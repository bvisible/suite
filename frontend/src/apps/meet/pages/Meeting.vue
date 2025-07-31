<template>
	<div class="h-screen bg-gray-900 flex flex-col overflow-hidden">
		<!-- Loading state -->
		<div v-if="isConnecting" class="flex-1 flex items-center justify-center">
			<div class="text-center text-white">
				<div
					class="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"
				></div>
				<p class="text-lg">Joining meeting...</p>
			</div>
		</div>

		<!-- Error state -->
		<div v-else-if="connectionError" class="flex-1 flex items-center justify-center">
			<div class="text-center text-white">
				<div class="text-red-500 mb-4">
					<lucide-alert-circle class="w-12 h-12 mx-auto" />
				</div>
				<p class="text-lg mb-4">{{ connectionError }}</p>
				<Button @click="joinMeetingRoom" variant="outline" theme="red"> Try Again </Button>
			</div>
		</div>

		<!-- Main video interface -->
		<template v-else>
			<!-- Meeting info bar -->
			<div class="bg-gray-800 px-6 py-2 flex-shrink-0 border-b border-gray-700">
				<div class="flex items-center justify-between">
					<div class="text-white">
						<span
							class="text-sm cursor-pointer hover:text-gray-300 transition-colors"
							@click="copyMeetingUrl"
							:title="'Click to copy meeting URL'"
						>
							{{ meetingDoc?.data?.title || meetingId }}
						</span>
					</div>
				</div>
			</div>

			<!-- Main video grid area -->
			<div class="flex-1 p-4 overflow-hidden">
				<div class="h-full grid gap-2" :class="gridClass">
					<!-- Local user video -->
					<div class="relative bg-gray-800 rounded-lg overflow-hidden min-h-0">
						<video
							ref="localVideo"
							class="w-full h-full object-cover transform scale-x-[-1]"
							autoplay
							muted
							playsinline
						/>
						<div
							class="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-sm"
						>
							{{ currentUser?.full_name || currentUser?.name || "You" }}
						</div>
						<div
							v-if="!isCameraOn"
							class="absolute inset-0 bg-gray-700 flex items-center justify-center"
						>
							<Avatar
								size="3xl"
								:label="userInitials"
								:image="userAvatar"
								class="mx-auto mb-4"
							/>
						</div>
					</div>

					<!-- Remote participants -->
					<div
						v-for="participant in participantsList"
						:key="participant.user_id"
						class="relative bg-gray-800 rounded-lg overflow-hidden min-h-0"
					>
						<video
							:ref="(el) => remoteVideos.set(participant.user_id, el)"
							class="w-full h-full object-cover"
							autoplay
							playsinline
						></video>
						<div
							v-if="participant.video_enabled"
							class="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-sm"
						>
							{{ participant.user_name }}
						</div>
						<div
							v-if="!participant.video_enabled"
							class="absolute inset-0 bg-gray-700 flex items-center justify-center"
						>
							<div class="text-white text-center">
								<div
									class="w-16 h-16 bg-gray-600 rounded-full flex items-center justify-center mx-auto mb-2"
								>
									<span class="text-white text-xl font-semibold">{{
										participant.initials
									}}</span>
								</div>
								<p class="text-sm">{{ participant.user_name }}</p>
							</div>
						</div>
						<div
							v-if="!participant.audio_enabled"
							class="absolute top-2 right-2 bg-gray-700 rounded-full p-1.5"
						>
							<lucide-mic-off class="w-4 h-4 text-white" />
						</div>
					</div>
				</div>
			</div>

			<!-- Bottom controls -->
			<div class="bg-gray-800 px-6 py-4 flex-shrink-0">
				<div class="flex items-center justify-center">
					<!-- Main controls -->
					<div class="flex items-center space-x-6">
						<!-- Microphone -->
						<Button
							@click="toggleMicrophone"
							:variant="isMicOn ? 'solid' : 'solid'"
							:theme="isMicOn ? 'gray' : 'red'"
							size="lg"
							class="w-12 h-12 rounded-full p-0"
							:title="
								'Toggle Audio (' + ($platform === 'mac' ? '⌘+D' : 'Ctrl+D') + ')'
							"
						>
							<template #icon>
								<lucide-mic-off v-if="!isMicOn" class="w-6 h-6 text-white" />
								<lucide-mic v-else class="w-6 h-6 text-white" />
							</template>
						</Button>

						<!-- Camera -->
						<Button
							@click="toggleCamera"
							:variant="isCameraOn ? 'solid' : 'solid'"
							:theme="isCameraOn ? 'gray' : 'red'"
							size="lg"
							class="w-12 h-12 rounded-full p-0"
							:title="
								'Toggle Video (' + ($platform === 'mac' ? '⌘+E' : 'Ctrl+E') + ')'
							"
						>
							<template #icon>
								<lucide-video-off v-if="!isCameraOn" class="w-6 h-6 text-white" />
								<lucide-video v-else class="w-6 h-6 text-white" />
							</template>
						</Button>

						<!-- End call -->
						<Button
							@click="endCall"
							variant="solid"
							size="lg"
							theme="red"
							class="w-12 h-12 rounded-full p-0"
							title="End Call"
						>
							<template #icon>
								<lucide-phone-off class="w-6 h-6 text-white" />
							</template>
						</Button>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import { Avatar, Button, getCachedDocumentResource } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { session } from "../data/session.js";
import {
	cleanupMediasoup,
	publishAudio,
	publishVideo,
} from "../mediasoup-client.js";
import {
	initSocket,
	joinMeeting,
	leaveMeeting,
	registerWebRTCEventHandlers,
	unregisterWebRTCEventHandlers,
} from "../socket.js";
import {
	getSFUMeetingManager,
	resetSFUMeetingManager,
} from "../utils/sfu-meeting-manager.js";

// Router access
const route = useRoute();
const router = useRouter();
const meetingId = computed(() => route.params.meetingId);

// Reactive state
const isMicOn = ref(true);
const isCameraOn = ref(true);
const isScreenSharing = ref(false);
const localVideo = ref(null);
const isConnecting = ref(true);
const connectionError = ref(null);

// User and participant data
const currentUser = ref(null);
const participants = ref(new Map());
const remoteVideos = ref(new Map());

// MediaSoup state
let localStream = null;
let videoProducer = null;
let audioProducer = null;
const consumers = ref(new Map());

// SFU Meeting Manager
let sfuManager = null;

// Computed grid class based on participant count
const gridClass = computed(() => {
	const totalParticipants = participants.value.size + 1; // +1 for local user
	if (totalParticipants === 1) return "grid-cols-1";
	if (totalParticipants === 2) return "grid-cols-2";
	if (totalParticipants <= 4) return "grid-cols-2 grid-rows-2";
	if (totalParticipants <= 6) return "grid-cols-3 grid-rows-2";
	return "grid-cols-4 grid-rows-2";
});

const userInitials = computed(() => {
	const name = currentUser.value.full_name || currentUser.value.name || "User";
	return name
		.split(" ")
		.map((n) => n[0])
		.join("")
		.toUpperCase()
		.slice(0, 2);
});
const userAvatar = computed(() => currentUser.value.avatar || "");

const participantsList = computed(() => {
	return Array.from(participants.value.values());
});

const meetingDoc = getCachedDocumentResource("Sae Meeting", meetingId.value);

// Control functions
const toggleMicrophone = async () => {
	try {
		if (audioProducer) {
			if (isMicOn.value) {
				await audioProducer.pause();
			} else {
				await audioProducer.resume();
			}
		}

		// Also update the local track
		if (localStream) {
			const audioTrack = localStream.getAudioTracks()[0];
			if (audioTrack) {
				audioTrack.enabled = !isMicOn.value;
			}
		}

		isMicOn.value = !isMicOn.value;
	} catch (error) {
		console.error("Error toggling microphone:", error);
	}
};

const toggleCamera = async () => {
	try {
		if (videoProducer) {
			if (isCameraOn.value) {
				await videoProducer.pause();
			} else {
				await videoProducer.resume();
			}
		}

		// Also update the local track
		if (localStream) {
			const videoTrack = localStream.getVideoTracks()[0];
			if (videoTrack) {
				videoTrack.enabled = !isCameraOn.value;
			}
		}

		isCameraOn.value = !isCameraOn.value;
	} catch (error) {
		console.error("Error toggling camera:", error);
	}
};

const endCall = async () => {
	try {
		// Leave the meeting
		await leaveMeeting(meetingId.value);

		// Clean up mediasoup resources
		cleanupMediasoup();

		// Clean up local media
		if (localStream) {
			for (const track of localStream.getTracks()) {
				track.stop();
			}
		}

		// Navigate back to home
		router.push({ name: "Home" });
	} catch (error) {
		console.error("Error ending call:", error);
		// Still navigate away even if there's an error
		router.push({ name: "Home" });
	}
};

const copyMeetingUrl = async () => {
	try {
		const meetingUrl = window.location.href;
		await navigator.clipboard.writeText(meetingUrl);
		console.log("Meeting URL copied to clipboard:", meetingUrl);
	} catch (error) {
		console.error("Failed to copy meeting URL:", error);
	}
};

const initializeCamera = async () => {
	try {
		console.log("Initializing camera and microphone...");
		localStream = await navigator.mediaDevices.getUserMedia({
			video: {
				width: { ideal: 1280 },
				height: { ideal: 720 },
				frameRate: { ideal: 30 },
			},
			audio: {
				echoCancellation: true,
				noiseSuppression: true,
				autoGainControl: true,
			},
		});

		console.log("Media stream obtained:", localStream);

		// Wait for the next tick to ensure the video element is ready
		await new Promise((resolve) => setTimeout(resolve, 100));

		if (localVideo.value) {
			localVideo.value.srcObject = localStream;
			console.log("Local video stream assigned to video element");

			// Ensure the video plays
			try {
				await localVideo.value.play();
				console.log("Local video started playing");
			} catch (playError) {
				console.warn(
					"Auto-play failed, but video should still work:",
					playError,
				);
			}
		} else {
			console.error("Local video element not found");
		}
	} catch (error) {
		console.error("Error accessing camera:", error);
		isCameraOn.value = false;
		connectionError.value = "Failed to access camera and microphone";
	}
};

const joinMeetingRoom = async () => {
	try {
		isConnecting.value = true;
		connectionError.value = null;

		// Get current user info from session
		if (!session.isLoggedIn) {
			throw new Error("User not logged in");
		}

		currentUser.value = {
			user_id: session.user.sessionUser,
			name: session.user.full_name,
			full_name: session.user.full_name,
			avatar: session.user.avatar,
		};

		// Initialize camera/audio first to show local stream
		await initializeCamera();

		// Step 1: Join the meeting in Frappe (authentication and permissions)
		const joinResult = await joinMeeting(meetingId.value);
		console.log("✅ Joined meeting in Frappe:", joinResult);

		// Step 2: Connect directly to SFU for WebRTC operations
		sfuManager = getSFUMeetingManager();
		sfuManager.initialize({
			meetingId: meetingId.value,
			currentUser,
			participants,
			consumers,
			remoteVideos,
			eventHandlers: {
				onParticipantJoined: (participant) => {
					console.log("📋 SFU participant joined handler:", participant);
				},
				onParticipantLeft: (data) => {
					console.log("📋 SFU participant left handler:", data);
				},
				onConsumerCreated: (consumer, data) => {
					console.log("📋 SFU consumer created handler:", consumer, data);
				},
				onSubscriptionError: (error, data) => {
					console.error("📋 SFU subscription error handler:", error, data);
				},
				onProducerClosed: (data) => {
					console.log("📋 SFU producer closed handler:", data);
				},
				onMediaControlUpdate: (data, participant) => {
					console.log(
						"📋 SFU media control update handler:",
						data,
						participant,
					);
				},
				onScreenShareStarted: (data) => {
					console.log("� SFU screen share started handler:", data);
				},
				onScreenShareStopped: (data) => {
					console.log("📋 SFU screen share stopped handler:", data);
				},
			},
		});

		await sfuManager.connect();

		// Hide loading indicator once we've joined
		isConnecting.value = false;

		// Step 3: Initialize mediasoup device with router capabilities from SFU
		await sfuManager.initializeDevice();

		// Step 4: Start publishing media if we have local stream
		if (localStream && sfuManager) {
			const publishOptions = {
				publishVideo: isCameraOn.value,
				publishAudio: isMicOn.value,
			};

			const mediaResults = await sfuManager.publishMedia(
				localStream,
				publishOptions,
			);
			videoProducer = mediaResults.videoProducer;
			audioProducer = mediaResults.audioProducer;
		}

		// Step 5: Request existing participants and their media streams
		// This will create receive transport on-demand when needed
		await requestExistingParticipants();

		console.log("🎉 Meeting join complete - using direct SFU architecture");
	} catch (error) {
		console.error("❌ Error joining meeting:", error);
		connectionError.value = error.message || "Failed to join meeting";
		isConnecting.value = false;
	}
};

const requestExistingParticipants = async () => {
	try {
		console.log("Requesting existing participants and their streams...");

		await sfuManager.setupExistingParticipants();
	} catch (error) {
		console.error("Error requesting existing participants:", error);
	}
};

const handleKeyDown = (event) => {
	if ((event.metaKey || event.ctrlKey) && event.key === "d") {
		event.preventDefault();
		toggleMicrophone();
	}
	if ((event.metaKey || event.ctrlKey) && event.key === "e") {
		event.preventDefault();
		toggleCamera();
	}
};

onMounted(async () => {
	window.addEventListener("keydown", handleKeyDown);

	// Join the meeting room
	await joinMeetingRoom();
});

// Watch for localVideo element and localStream to ensure they connect
watch(
	[localVideo, () => localStream],
	async ([videoElement, stream]) => {
		if (videoElement && stream && !videoElement.srcObject) {
			console.log("Connecting local stream to video element");
			videoElement.srcObject = stream;
			try {
				await videoElement.play();
			} catch (error) {
				console.warn("Auto-play failed for local video:", error.message);
				// Local video autoplay failure is less critical since user can see themselves
			}
		}
	},
	{ immediate: true },
);

onUnmounted(async () => {
	// Clean up WebRTC event handlers
	unregisterWebRTCEventHandlers();

	// Clean up SFU manager
	if (sfuManager) {
		sfuManager.cleanup();
	}

	// Reset SFU manager instance
	resetSFUMeetingManager();

	// Leave meeting in Frappe
	try {
		await leaveMeeting(meetingId.value);
		console.log("✅ Left meeting in Frappe");
	} catch (error) {
		console.error("❌ Error leaving meeting:", error);
	}

	// Clean up mediasoup resources
	cleanupMediasoup();

	// Clean up media streams
	if (localStream) {
		for (const track of localStream.getTracks()) {
			track.stop();
		}
	}

	window.removeEventListener("keydown", handleKeyDown);
});
</script>
