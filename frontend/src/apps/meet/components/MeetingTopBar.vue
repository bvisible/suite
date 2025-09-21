<template>
	<Transition
		enter-active-class="transition-all duration-300 ease-out"
		enter-from-class="opacity-0 transform -translate-y-4"
		enter-to-class="opacity-100 transform translate-y-0"
		leave-active-class="transition-all duration-300 ease-in"
		leave-from-class="opacity-100 transform translate-y-0"
		leave-to-class="opacity-0 transform -translate-y-4"
	>
		<div v-show="isVisible" class="bg-gray-800 px-6 py-3 flex-shrink-0">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<FrappeMeetingLogo class="h-8" />
					<h4 class="text-white text-base">Frappe Meet</h4>
				</div>
				<div
					class="text-white cursor-pointer hover:text-gray-300 transition-colors space-x-2"
					@click="copyMeetingUrl"
				>
					<span class="text-sm" :title="'Click to copy meeting URL'">
						{{ meetingTitle || meetingId }}
					</span>
					<lucide-copy class="w-4 h-4 inline-block ml-1" />
				</div>
			</div>
		</div>
	</Transition>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import FrappeMeetingLogo from "../icons/FrappeMeetingLogo.vue";

defineProps({
	meetingTitle: {
		type: String,
		default: "",
	},
	meetingId: {
		type: String,
		required: true,
	},
});

// Auto-hide functionality
const isVisible = ref(true);
let hideTimeout = null;

const showTopBar = () => {
	isVisible.value = true;
	resetHideTimer();
};

const resetHideTimer = () => {
	if (hideTimeout) {
		clearTimeout(hideTimeout);
	}
	hideTimeout = setTimeout(() => {
		isVisible.value = false;
	}, 3000);
};

const handleActivity = () => {
	showTopBar();
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

onMounted(() => {
	resetHideTimer();

	document.addEventListener("mousemove", handleActivity);
	document.addEventListener("mousedown", handleActivity);
	document.addEventListener("keydown", handleActivity);
	document.addEventListener("touchstart", handleActivity);
	document.addEventListener("touchmove", handleActivity);
});

onUnmounted(() => {
	if (hideTimeout) {
		clearTimeout(hideTimeout);
	}

	document.removeEventListener("mousemove", handleActivity);
	document.removeEventListener("mousedown", handleActivity);
	document.removeEventListener("keydown", handleActivity);
	document.removeEventListener("touchstart", handleActivity);
	document.removeEventListener("touchmove", handleActivity);
});
</script>
