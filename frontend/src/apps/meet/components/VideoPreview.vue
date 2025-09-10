<template>
	<div class="relative">
		<div class="bg-gray-900 rounded-lg overflow-hidden shadow-lg aspect-video relative">
			<video
				ref="videoElement"
				autoplay
				muted
				playsinline
				class="w-full h-full object-cover transform scale-x-[-1]"
			/>
			<div
				v-if="!videoTrack"
				class="absolute inset-0 bg-black bg-opacity-20 flex items-center justify-center"
			>
				<div class="text-white text-center">
					<MeetingAvatar
						:label="userInitials"
						:image="userAvatar"
						:tiles="videoPreviewTiles"
						class="mx-auto mb-4"
					/>
					<p class="text-lg font-medium">{{ userName }}</p>
				</div>
			</div>
		</div>

		<!-- Video controls -->
		<div class="flex justify-center mt-4 space-x-4">
			<Button
				:variant="isMuted ? 'solid' : 'outline'"
				@click="toggleMute"
				size="lg"
				class="p-2"
				:title="'Toggle Audio (' + ($platform === 'mac' ? '⌘+D' : 'Ctrl+D') + ')'"
			>
				<template #icon>
					<lucide-mic-off v-if="isMuted" />
					<lucide-mic v-else />
				</template>
			</Button>
			<Button
				:variant="isVideoOff ? 'solid' : 'outline'"
				@click="toggleVideo"
				size="lg"
				class="p-2"
				:title="'Toggle Video (' + ($platform === 'mac' ? '⌘+E' : 'Ctrl+E') + ')'"
			>
				<template #icon>
					<lucide-video-off v-if="isVideoOff" />
					<lucide-video v-else />
				</template>
			</Button>
		</div>
	</div>
</template>

<script setup>
import {
	cameraEnabled,
	micEnabled,
	setCameraEnabled,
	setMicEnabled,
} from "@/data/mediaPreferences.js";
import { Button } from "frappe-ui";
import { onMounted, onUnmounted, ref } from "vue";
import MeetingAvatar from "./MeetingAvatar.vue";

const videoElement = ref(null);
const isMuted = ref(!micEnabled.value);
const isVideoOff = ref(!cameraEnabled.value);

const audioTrack = ref(null);
const videoTrack = ref(null);
const composedStream = ref(null);

const userName = ref("You");
const userInitials = ref("Y");
const userAvatar = ref("");
// When preview is shown in different layouts this helps scale placeholder
const videoPreviewTiles = 1;

function rebuildStream() {
	const tracks = [];
	if (videoTrack.value) tracks.push(videoTrack.value);
	if (audioTrack.value) tracks.push(audioTrack.value);
	if (tracks.length) {
		composedStream.value = new MediaStream(tracks);
		if (videoElement.value) {
			// Re-attach only if changed
			if (videoElement.value.srcObject !== composedStream.value) {
				videoElement.value.srcObject = composedStream.value;
			}
		}
	} else {
		composedStream.value = null;
		if (videoElement.value) videoElement.value.srcObject = null;
	}
}

async function acquire(kind) {
	try {
		if (kind === "video" && !videoTrack.value) {
			const stream = await navigator.mediaDevices.getUserMedia({
				video: true,
				audio: false,
			});
			videoTrack.value = stream.getVideoTracks()[0] || null;
			if (videoTrack.value)
				videoTrack.value.onended = () => {
					videoTrack.value = null;
					rebuildStream();
				};
		} else if (kind === "audio" && !audioTrack.value) {
			const stream = await navigator.mediaDevices.getUserMedia({
				audio: true,
				video: false,
			});
			audioTrack.value = stream.getAudioTracks()[0] || null;
			if (audioTrack.value)
				audioTrack.value.onended = () => {
					audioTrack.value = null;
					rebuildStream();
				};
		}
		rebuildStream();
	} catch (err) {
		console.error(`Error acquiring ${kind} track:`, err);
		// Revert toggle state on failure
		if (kind === "video") isVideoOff.value = true;
		else isMuted.value = true;
	}
}

async function acquireBoth() {
	try {
		const stream = await navigator.mediaDevices.getUserMedia({
			audio: true,
			video: true,
		});
		videoTrack.value = stream.getVideoTracks()[0] || null;
		audioTrack.value = stream.getAudioTracks()[0] || null;
		if (videoTrack.value)
			videoTrack.value.onended = () => {
				videoTrack.value = null;
				rebuildStream();
			};
		if (audioTrack.value)
			audioTrack.value.onended = () => {
				audioTrack.value = null;
				rebuildStream();
			};
		rebuildStream();
	} catch (err) {
		console.error("Error acquiring audio+video:", err);
		if (err && err.name === "NotAllowedError") {
			// Reflect denied permissions in UI
			isVideoOff.value = true;
			isMuted.value = true;
		}
	}
}

function stopTrack(kind) {
	const t = kind === "video" ? videoTrack : audioTrack;
	if (t.value) {
		try {
			t.value.stop();
		} catch (_) {
			/* ignore */
		}
		t.value = null;
	}
	rebuildStream();
}

async function toggleVideo() {
	if (isVideoOff.value) {
		isVideoOff.value = false;
		await acquire("video");
	} else {
		isVideoOff.value = true;
		stopTrack("video");
	}
	setCameraEnabled(!isVideoOff.value);
}

async function toggleMute() {
	if (isMuted.value) {
		isMuted.value = false;
		await acquire("audio");
	} else {
		isMuted.value = true;
		stopTrack("audio");
	}
	setMicEnabled(!isMuted.value);
}

const handleKeyDown = (event) => {
	if ((event.metaKey || event.ctrlKey) && event.key === "d") {
		event.preventDefault();
		toggleMute();
	}
	if ((event.metaKey || event.ctrlKey) && event.key === "e") {
		event.preventDefault();
		toggleVideo();
	}
};

onMounted(() => {
	// Only acquire what user has enabled in preferences
	if (!isMuted.value && !isVideoOff.value) {
		acquireBoth();
	} else {
		if (!isMuted.value) acquire("audio");
		if (!isVideoOff.value) acquire("video");
	}
	window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
	stopTrack("video");
	stopTrack("audio");
	window.removeEventListener("keydown", handleKeyDown);
});
</script>
