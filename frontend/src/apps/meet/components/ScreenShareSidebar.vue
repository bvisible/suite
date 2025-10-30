<template>
	<TransitionGroup
		name="tile"
		tag="div"
		class="overflow-y-auto p-1 grid gap-2 h-full"
		:class="sidebarClass"
		:style="sidebarStyle"
	>
		<!-- Local camera tile -->
		<div
			key="local-camera-sidebar"
			class="relative w-full bg-gray-800 rounded overflow-hidden flex"
			:style="singleTileStyle"
		>
			<video
				:ref="setLocalVideoRef"
				class="w-full h-full object-cover transform scale-x-[-1] flex-1"
				autoplay
				muted
				playsinline
			/>
			<div
				v-if="!isCameraOn"
				class="absolute inset-0 bg-gray-700 flex items-center justify-center"
			>
				<MeetingAvatar
					:label="userInitials"
					:image="userAvatar"
					:tiles="visibleTileCount"
				/>
			</div>
			<NamePill name="You" size="sm" position="bottom-left" />

			<div v-if="isMicOn && localStream" class="absolute top-1 right-1 rounded-full bg-gray-700 p-1">
				<AudioIndicator
					:mediaStream="localStream"
					:isActive="true"
					:maxHeight="12"
					:sensitivity="3.0"
					activeColorClass="bg-gray-100"
				/>
			</div>
			<div
				v-if="!isMicOn"
				class="absolute top-1 right-1 bg-gray-700 rounded-full p-1"
			>
				<lucide-mic-off class="w-3 h-3 text-white" />
			</div>
		</div>

		<!-- Remote participants -->
		<div
			v-for="participant in sidebarDisplay.list"
			:key="'side-' + participant.user_id"
			class="relative w-full bg-gray-800 rounded overflow-hidden flex"
			:style="singleTileStyle"
		>
			<video
				:ref="(el) => setRemoteVideoRef(participant.user_id, el)"
				:participant-id="participant.user_id"
				class="w-full h-full object-cover flex-1 remote-video"
				autoplay
				muted
				playsinline
			></video>
			<div
				v-if="!participant.video_enabled"
				class="absolute inset-0 flex items-center justify-center bg-gray-700"
			>
				<MeetingAvatar
					:image="participant.avatar"
					:label="participant.initials"
					:tiles="visibleTileCount"
				/>
			</div>
			<NamePill :name="participant.user_name" size="sm" position="bottom-left" />

			<div v-if="participant.audio_enabled && participantStreams[participant.user_id]" class="absolute top-1 right-1">
				<AudioIndicator
					:mediaStream="participantStreams[participant.user_id]"
					:isActive="true"
					:maxHeight="12"
					:sensitivity="3.0"
					activeColorClass="bg-gray-100"
				/>
			</div>
			<div
				v-if="!participant.audio_enabled"
				class="absolute top-1 right-1 bg-gray-700 rounded-full p-1"
			>
				<lucide-mic-off class="w-3 h-3 text-white" />
			</div>
		</div>

		<!-- Grouping tile -->
		<div
			v-if="sidebarDisplay.extra > 0"
			key="sidebar-group"
			:title="hiddenParticipantsTooltip"
				class="relative w-full bg-gray-800/70 rounded overflow-hidden flex items-center justify-center cursor-pointer"
		>
			<div class="text-xs text-white text-center px-2 leading-snug">
				and {{ sidebarDisplay.extra }} others
			</div>
		</div>
	</TransitionGroup>
</template>

<script setup>
import { computed, inject } from "vue";
import { useAudioStream } from "../composables/useAudioLevels.js";
import { useScreenShareSidebar } from "../composables/useScreenShareSidebar.js";
import { getSFUMeetingManager } from "../utils/sfu-meeting-manager.js";
import AudioIndicator from "./AudioIndicator.vue";
import MeetingAvatar from "./MeetingAvatar.vue";
import NamePill from "./NamePill.vue";

const props = defineProps({
	participants: {
		type: Object,
		required: true,
	},
	currentUser: {
		type: Object,
		required: true,
	},
	isCameraOn: {
		type: Boolean,
		default: false,
	},
	isMicOn: {
		type: Boolean,
		default: false,
	},
	activeSpeakerIds: {
		type: Array,
		default: () => [],
	},
});

const setLocalVideoRef = inject("setLocalVideoRef");
const setRemoteVideoRef = inject("setRemoteVideoRef");

const userInitials = computed(() => {
	const name = props.currentUser?.full_name || props.currentUser?.name || "You";
	return name
		.split(" ")
		.map((n) => n[0])
		.join("")
		.toUpperCase()
		.slice(0, 2);
});

const userAvatar = computed(() => props.currentUser?.avatar || "");
const activeSpeakerIds = computed(() => props.activeSpeakerIds);

const {
	sidebarDisplay,
	sidebarClass,
	sidebarStyle,
	singleTileStyle,
	visibleTileCount,
	hiddenParticipantsTooltip,
} = useScreenShareSidebar(props.participants, activeSpeakerIds);

const { stream: localStream } = useAudioStream(props.currentUser?.user_id);

const participantStreams = computed(() => {
	const streams = {};
	for (const participant of Object.values(props.participants)) {
		try {
			const sfuManager = getSFUMeetingManager();
			if (sfuManager?.consumerManager) {
				const audioConsumer = sfuManager.consumerManager.getAudioConsumer(
					participant.user_id,
				);
				if (audioConsumer?.track) {
					streams[participant.user_id] = new MediaStream([audioConsumer.track]);
				}
			}
		} catch (error) {
			console.error(
				"Error getting stream for participant:",
				participant.user_id,
				error,
			);
		}
	}
	return streams;
});
</script>

<style scoped>
/* Transition styles */
.tile-enter-from,
.tile-leave-to {
	opacity: 0;
	transform: scale(0.85) translateY(8px);
}

.tile-enter-active,
.tile-leave-active {
	transition:
		opacity 200ms ease,
		transform 200ms ease;
}

.tile-move {
	transition: transform 200ms ease;
}

.tile-leave-active {
	position: absolute;
	top: 0;
	left: 0;
	width: 100%;
	height: 100%;
	pointer-events: none;
}

.remote-video {
	background-color: #000;
	will-change: transform;
	transform: translateZ(0);
}

@-moz-document url-prefix() {
	.remote-video {
		background-color: #111;
		opacity: 0.99;
	}
}
</style>
