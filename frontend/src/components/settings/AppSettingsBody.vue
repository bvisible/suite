<template>
	<!-- Inside a mobile settings page (see mail's PWASettings): plain page-padded
	     flow — the sub-page container scrolls. Desktop keeps the dialog's padded
	     ScrollArea untouched. -->
	<div v-if="mobilePage" class="px-4 pb-8 pt-4">
		<slot />
	</div>
	<SettingsBody v-else v-bind="$attrs">
		<div class="pt-6">
			<slot />
		</div>
	</SettingsBody>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { SettingsBody } from 'frappe-ui'

defineOptions({ inheritAttrs: false })

const mobilePage = inject('app-settings-mobile-page', false)
</script>
