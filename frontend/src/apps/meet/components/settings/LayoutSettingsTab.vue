<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
<template>
	<AppSettingsHeader
		:title="__('Layout')"
		:description="__('Customize the meeting interface layout')"
	/>
	<AppSettingsBody>
		<div class="space-y-6">
			<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
			<SettingsRow
				:title="__('Auto-hide header and controls')"
				:description="__('Automatically hide the header and toolbar after 10 seconds of inactivity')"
			>
				<Switch v-model="autoHideToolbarLocal" />
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
	autoHideToolbar,
	setAutoHideToolbar,
} from "../../data/mediaPreferences";

const autoHideToolbarLocal: Ref<boolean> = ref(autoHideToolbar.value);

watch(autoHideToolbarLocal, (newValue) => {
	setAutoHideToolbar(newValue);
});

watch(autoHideToolbar, (newValue) => {
	autoHideToolbarLocal.value = newValue;
});
</script>
