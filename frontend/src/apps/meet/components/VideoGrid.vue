<template>
	<TransitionGroup
		name="tile"
		tag="div"
		class="flex-1 grid gap-2 min-h-0 call-grid transition-all duration-300 ease-out"
		:class="gridClass"
		:style="gridStyle"
	>
		<!-- Local user video -->
		<ParticipantTile
			:key="'local-' + localParticipant.user_id"
			:participant="localParticipant"
			:isLocal="true"
			:isVideoEnabled="isCameraOn"
			:isAudioEnabled="isMicOn"
			:isActiveSpeaker="activeSpeakerIds.includes(localParticipant.user_id)"
			:videoRef="setLocalVideoRef"
			:tileCount="visibleTileCount"
		/>

		<!-- Remote participants -->
		<ParticipantTile
			v-for="participant in displayParticipants.list"
			:key="'grid-' + participant.user_id"
			:participant="participant"
			:isLocal="false"
			:isVideoEnabled="participant.video_enabled"
			:isAudioEnabled="participant.audio_enabled"
			:isActiveSpeaker="activeSpeakerIds.includes(participant.user_id)"
			:videoRef="(el) => setRemoteVideoRef(participant.user_id, el)"
			:tileCount="visibleTileCount"
		/>

		<!-- Grouping tile for overflow participants -->
		<GroupTile
			v-if="displayParticipants.extra > 0"
			key="grid-group"
			:count="displayParticipants.extra"
			:tooltip="hiddenParticipantsTooltip"
		/>
	</TransitionGroup>
</template>

<script setup>
import { computed, inject } from "vue";
import { useVideoGridLayout } from "../composables/useVideoGridLayout.js";
import { getInitials } from "../utils/text";
import GroupTile from "./GroupTile.vue";
import ParticipantTile from "./ParticipantTile.vue";

const meetingState = inject("meetingState");
const setLocalVideoRef = inject("setLocalVideoRef");
const setRemoteVideoRef = inject("setRemoteVideoRef");

const participants = computed(() => meetingState.participants.value);
const currentUser = computed(() => meetingState.currentUser.value);
const isCameraOn = computed(() => meetingState.isCameraOn.value);
const isMicOn = computed(() => meetingState.isMicOn.value);
const activeSpeakerIds = computed(() => meetingState.activeSpeakerIds.value);

const localParticipant = computed(() => {
	const userIdRaw = currentUser.value?.user_id;
	const fullNameRaw = currentUser.value?.full_name;
	const nameRaw = currentUser.value?.name;
	const avatarRaw = currentUser.value?.avatar;

	const user_id =
		typeof userIdRaw === "string"
			? userIdRaw
			: userIdRaw == null
				? "local"
				: String(userIdRaw);
	const displayNameRaw = fullNameRaw ?? nameRaw ?? "You";
	const user_name =
		typeof displayNameRaw === "string"
			? displayNameRaw
			: String(displayNameRaw);
	const avatar =
		typeof avatarRaw === "string"
			? avatarRaw
			: avatarRaw == null
				? ""
				: String(avatarRaw);

	return {
		user_id,
		user_name,
		avatar,
		initials: getInitials(user_name),
	};
});

const {
	displayParticipants,
	gridClass,
	gridStyle,
	visibleTileCount,
	hiddenParticipantsTooltip,
} = useVideoGridLayout(participants, activeSpeakerIds);
</script>
