<template>
	<div
		class="flex min-h-11 items-center gap-3 rounded-6 px-3 py-1.5 transition-colors hover:bg-surface-gray-2"
		:data-testid="`people-participant-${participant.user_id}`"
		:data-audio-enabled="participant.audio_enabled ? 'true' : 'false'"
	>
		<MeetAvatar
			size="lg"
			:image="participant.avatar"
			:label="participant.user_name || participant.user_id"
		/>

		<div class="min-w-0 flex-1">
			<div class="flex items-center gap-2">
				<span class="truncate text-sm text-ink-gray-8 tracking-[0.28px]">
					{{ participant.user_name }}
				</span>
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<span v-if="isCurrentUser" class="text-xs text-ink-gray-5">{{ __('(You)') }}</span>
			</div>
		</div>

		<div class="ml-auto flex shrink-0 items-center justify-end gap-1">
			<span
				v-if="isHost"
				class="rounded-full bg-surface-gray-4 px-1.5 py-px text-xs text-ink-gray-6 tracking-[0.24px]"
			>
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				{{ __('Host') }}
			</span>
			<span
				v-if="participant.is_guest"
				class="rounded-full bg-surface-gray-4 px-1.5 py-px text-xs text-ink-gray-6 tracking-[0.24px]"
			>
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				{{ __('Guest') }}
			</span>
		</div>

		<div class="flex flex-shrink-0 items-center gap-1">
			<!-- Raised Hand Indicator -->
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<div v-if="isHandRaised" class="flex items-center justify-center p-1.5 rounded-6" :title="__('{0} has raised their hand', [participant.user_name || participant.user_id])">
				<div class="rounded-full bg-amber-500 p-0.5">
					<lucide-hand class="w-3.5 h-3.5 text-ink-gray-9" />
				</div>
			</div>

			<!-- Video Status -->
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<span
				class="flex items-center justify-center p-1.5 text-ink-gray-6"
				:title="participant.video_enabled ? __('Camera on') : __('Camera off')"
			>
				<MeetCameraIcon v-if="participant.video_enabled" class="size-4" />
				<MeetCameraOffIcon v-else class="size-4" />
			</span>

			<!-- Audio Status -->
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<span
				class="flex items-center justify-center p-1.5 text-ink-gray-6"
				:title="participant.audio_enabled ? __('Microphone on') : __('Microphone off')"
			>
				<MeetMicIcon v-if="participant.audio_enabled" class="size-4" />
				<MeetMicOffIcon v-else class="size-4" />
			</span>

			<!-- Host Controls -->
			<div v-if="canControlParticipant" class="relative">
				<Dropdown :options="hostOptions">
					<template #default>
						<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
						<button
							class="flex items-center justify-center rounded-6 p-1.5 text-ink-gray-6 hover:bg-surface-gray-3"
							:aria-label="__('Actions for {0}', [participant.user_name || participant.user_id])"
							:data-testid="`people-participant-actions-${participant.user_id}`"
						>
							<lucide-more-horizontal class="w-4 h-4" />
						</button>
					</template>
				</Dropdown>
			</div>
			<div v-else-if="reserveHostControlSpace" class="w-7 shrink-0" aria-hidden="true" />
		</div>
	</div>

	<!-- Kick Confirmation Dialog -->
	<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
	<KickParticipantDialog
		v-model="showKickDialog"
		:participant-name="participant.user_name || __('this participant')"
		:can-ban="participant.is_guest === true"
		@confirm="handleKickConfirm"
	/>
</template>

<script setup lang="ts">
import { Dropdown } from "frappe-ui";
import { computed, ref } from "vue";
import { useMeetingContext } from "../composables/useMeetingContext";
import MeetCameraIcon from "../icons/MeetCameraIcon.vue";
import MeetCameraOffIcon from "../icons/MeetCameraOffIcon.vue";
import MeetMicIcon from "../icons/MeetMicIcon.vue";
import MeetMicOffIcon from "../icons/MeetMicOffIcon.vue";
import type { Participant } from "../utils/media/ParticipantManager";
import KickParticipantDialog from "./KickParticipantDialog.vue";
import MeetAvatar from "./MeetAvatar.vue";

interface Props {
	participant: Participant;
	isCurrentUser?: boolean;
	isHost?: boolean;
	canControlParticipant?: boolean;
	reserveHostControlSpace?: boolean;
	canPromoteToCohost?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
	isCurrentUser: false,
	isHost: false,
	canControlParticipant: false,
	reserveHostControlSpace: false,
	canPromoteToCohost: false,
});

const emit = defineEmits<{
	muteParticipant: [participantId: string];
	kickParticipant: [participantId: string, ban: boolean];
	lowerHand: [participantId: string];
	promoteToCohost: [participantId: string];
}>();

const meetingCtx = useMeetingContext();
const showKickDialog = ref(false);

const isHandRaised = computed(() => {
	if (!meetingCtx?.raiseHandStore?.raisedHands) return false;
	return !!meetingCtx.raiseHandStore.raisedHands[props.participant.user_id];
});

const handleKickConfirm = (ban: boolean) => {
	emit("kickParticipant", props.participant.user_id, ban);
	showKickDialog.value = false;
};

const hostOptions = computed(() => {
	return [
        {
            icon: "lucide-mic-off",
            // //// Neoffice — i18n: text a person reads goes through __() (#1316)
            label: __('Mute'),
			condition: () => !!props.participant.audio_enabled,
			onClick: () => emit("muteParticipant", props.participant.user_id),
		},
		{
            icon: "lucide-hand",
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			label: __('Lower Hand'),
			condition: () => isHandRaised.value,
			onClick: () => emit("lowerHand", props.participant.user_id),
		},
		{
			icon: "lucide-user-shield",
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			label: __('Promote to Co-host'),
			condition: () => props.canPromoteToCohost,
			onClick: () => emit("promoteToCohost", props.participant.user_id),
		},
		{
            icon: "lucide-user-x",
            // //// Neoffice — i18n: text a person reads goes through __() (#1316)
            label: __('Remove'),
			onClick: () => {
				showKickDialog.value = true;
			},
		},
	];
});
</script>
