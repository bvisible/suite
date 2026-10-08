<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
<template>
	<AppSettingsHeader
		:title="__('Controls')"
		:description="__('Manage join rules, chat, and security for this meeting.')"
	/>
	<AppSettingsBody>
			<div>
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<SettingsRow
					:title="__('Allow Guests')"
					:description="__('Allow non-registered users to join this meeting')"
				>
					<Switch
						v-model="allowGuest"
						:disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
					/>
				</SettingsRow>

				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<SettingsRow
					:title="__('Require host approval')"
					:description="__('People wait in the lobby until a host or co-host admits them')"
				>
					<Switch
						v-model="requireHostApproval"
						:disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
					/>
				</SettingsRow>

				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<SettingsRow
					:title="__('Host Only Chat')"
					:description="__('Restrict chat so only hosts and co-hosts can send messages')"
				>
					<Switch
						v-model="hostOnlyChat"
						:disabled="meetingDoc.updateSettings.loading || meetingDoc.get.loading"
					/>
				</SettingsRow>

				<E2EESettingsSection
					:meeting-id="props.meetingId"
					:meeting-doc="meetingDoc"
					:globally-enabled="globalE2EEEnabled"
				/>
			</div>
	</AppSettingsBody>
</template>

<script setup lang="ts">
import AppSettingsHeader from '@/components/settings/AppSettingsHeader.vue'
import AppSettingsBody from '@/components/settings/AppSettingsBody.vue'
import {
	debounce,
	SettingsRow,
	Switch,
	toast,
} from 'frappe-ui';
import { computed, onMounted, ref, watch } from "vue";
import { useChatStore } from "@/apps/meet/composables/useChatStore";
import { useMeetingDoc } from "../../composables/useMeetingDoc";
import E2EESettingsSection from "./E2EESettingsSection.vue";

const props = defineProps({
	meetingId: {
		type: String,
		required: true,
	},
});

const {
	getMeetingDoc,
	allowGuest: globalAllowGuest,
	meetingType: globalMeetingType,
	e2eeEnabled: globalE2EEEnabled,
} = useMeetingDoc();

const chatStore = useChatStore();

const allowGuest = ref<boolean>(globalAllowGuest.value);
const meetingType = ref<string>(globalMeetingType.value);
const hostOnlyChat = ref<boolean>(chatStore.hostOnlyChat);

const requireHostApproval = computed({
	get: () => meetingType.value === "restricted",
	set: (enabled: boolean) => {
		meetingType.value = enabled ? "restricted" : "open";
	},
});

const meetingDoc = getMeetingDoc(props.meetingId);

onMounted(async () => {
	try {
		allowGuest.value = globalAllowGuest.value;
		meetingType.value = globalMeetingType.value;
		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	} catch (error) {
		console.error("Failed to load meeting settings");
	}
});

const saveSettings = debounce(async () => {
	if (meetingDoc.updateSettings.loading) return;

	try {
		await meetingDoc.updateSettings.submit({
			allow_guest: allowGuest.value,
			meeting_type: meetingType.value,
			host_only_chat: hostOnlyChat.value,
		});

		await meetingDoc.reload();
	} catch (error) {
		console.error("Failed to update meeting settings:", error);
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		toast.error(__('Failed to update meeting settings'));

		if (meetingDoc.doc?.host_only_chat !== undefined) {
			hostOnlyChat.value = !!meetingDoc.doc.host_only_chat;
		}
	}
}, 300);

watch(hostOnlyChat, (newValue) => {
	chatStore.hostOnlyChat = newValue;
});
watch([allowGuest, meetingType, hostOnlyChat], () => {
	if (!meetingDoc.get.loading) {
		saveSettings();
	}
});
</script>
