<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
<template>
	<AppSettingsHeader
		:title="__('Notifications')"
		:description="__('Customize notification sounds for meeting events')"
	/>
	<AppSettingsBody>
		<div class="space-y-6">
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<SettingsRow
				:title="__('Enable notification sounds')"
				:description="__('Play sounds for all meeting events')"
			>
				<Switch v-model="notificationChimesEnabledLocal" />
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
	notificationChimesEnabled,
	setNotificationChimesEnabled,
} from "../../data/notificationPreferences";

const notificationChimesEnabledLocal: Ref<boolean> = ref(
	notificationChimesEnabled.value,
);

watch(notificationChimesEnabledLocal, (newValue) => {
	setNotificationChimesEnabled(newValue);
});
</script>
