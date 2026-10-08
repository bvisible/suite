<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
<template>
	<AppSettingsHeader
		:title="__('Audio')"
		:description="__('Configure your audio and microphone settings')"
	/>
	<AppSettingsBody>
		<div>
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<SettingsRow
				:title="__('Noise Cancellation')"
				:description="__('Reduce background noise from your microphone')"
			>
				<Switch v-model="noiseCancellationEnabledLocal" />
			</SettingsRow>
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<SettingsRow
				:title="__('Push to Talk')"
				:description="__('Hold spacebar to unmute your microphone')"
			>
				<Switch v-model="pushToTalkEnabledLocal" />
			</SettingsRow>
		</div>
	</AppSettingsBody>
</template>

<script setup lang="ts">
import AppSettingsHeader from '@/components/settings/AppSettingsHeader.vue'
import AppSettingsBody from '@/components/settings/AppSettingsBody.vue'
import { SettingsRow, Switch } from "frappe-ui";
import { type Ref, ref, watch } from "vue";
import {
	noiseCancellationEnabled,
	pushToTalkEnabled,
	setNoiseCancellationEnabled,
	setPushToTalkEnabled,
} from "../../data/mediaPreferences";

const noiseCancellationEnabledLocal: Ref<boolean> = ref(
	noiseCancellationEnabled.value,
);

watch(noiseCancellationEnabledLocal, (newValue) => {
	setNoiseCancellationEnabled(newValue);
});

watch(noiseCancellationEnabled, (newValue) => {
	noiseCancellationEnabledLocal.value = newValue;
});

const pushToTalkEnabledLocal: Ref<boolean> = ref(pushToTalkEnabled.value);

watch(pushToTalkEnabledLocal, (newValue) => {
	setPushToTalkEnabled(newValue);
});

watch(pushToTalkEnabled, (newValue) => {
	pushToTalkEnabledLocal.value = newValue;
});
</script>
