<template>
	<div class="flex-1 flex min-h-0 overflow-hidden mb-2">
		<div
			class="flex-1 relative bg-black rounded-lg overflow-hidden flex items-center justify-center"
		>
			<template v-for="(share, idx) in displayScreenShares" :key="share.consumerId">
				<!-- Render only the first (focused) screen share -->
				<video
					v-if="idx === 0"
					:ref="setScreenShareVideoRef"
					:data-participant-id="share.participantId"
					class="w-full h-full object-contain bg-gray-900"
					autoplay
					playsinline
					muted
				></video>
			</template>

			<div class="absolute top-2 left-2 w-full">
				<NamePill
					v-if="displayScreenShares.length"
					:name="getScreensharerName"
					size="sm"
					position="top-left"
				/>
			</div>
		</div>

		<ScreenShareSidebar class="ml-3" />
	</div>
</template>

<script setup>
import { computed, inject } from "vue";
import NamePill from "./NamePill.vue";
import ScreenShareSidebar from "./ScreenShareSidebar.vue";

// Inject meeting state and functions
const meetingState = inject("meetingState");
const setScreenShareVideoRef = inject("setScreenShareVideoRef");
const getParticipantName = inject("getParticipantName");

const displayScreenShares = computed(
	() => meetingState.displayScreenShares.value,
);
const currentUser = computed(() => meetingState.currentUser.value);

const getScreensharerName = computed(() => {
	const firstShare = displayScreenShares.value[0];

	if (currentUser.value?.user_id === firstShare?.participantId) {
		return "Your screen";
	}
	if (firstShare) {
		return `${getParticipantName(firstShare.participantId)}'s screen`;
	}
});
</script>
