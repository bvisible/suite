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
				v-if="!stream || isVideoOff"
				class="absolute inset-0 bg-black bg-opacity-20 flex items-center justify-center"
			>
				<div class="text-white text-center">
					<Avatar
						size="2xl"
						:label="userInitials"
						:image="userAvatar"
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
import { Avatar, Button, Tooltip } from "frappe-ui";
import { onMounted, onUnmounted, ref } from "vue";

const videoElement = ref(null);
const isMuted = ref(false);
const isVideoOff = ref(false);
const stream = ref(null);

const userName = ref("You");
const userInitials = ref("Y");
const userAvatar = ref("");

const startCamera = async () => {
	try {
		stream.value = await navigator.mediaDevices.getUserMedia({
			video: true,
			audio: true,
		});
		if (videoElement.value) {
			videoElement.value.srcObject = stream.value;
		}
	} catch (error) {
		console.error("Error accessing camera:", error);
	}
};

const stopCamera = () => {
	if (stream.value) {
		for (const track of stream.value.getTracks()) {
			track.stop();
		}
		stream.value = null;
	}
};

const toggleMute = () => {
	isMuted.value = !isMuted.value;
	if (stream.value) {
		const audioTrack = stream.value.getAudioTracks()[0];
		if (audioTrack) {
			audioTrack.enabled = !isMuted.value;
		}
	}
};

const toggleVideo = () => {
	isVideoOff.value = !isVideoOff.value;
	if (stream.value) {
		const videoTrack = stream.value.getVideoTracks()[0];
		if (videoTrack) {
			videoTrack.enabled = !isVideoOff.value;
		}
	}
};

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
	startCamera();
	window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
	stopCamera();
	window.removeEventListener("keydown", handleKeyDown);
});
</script>
