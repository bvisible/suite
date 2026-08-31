<template>
	<!-- Inside a mobile settings page (see mail's PWASettings) the page's top bar
	     already shows the section title and hosts the actions (teleported into
	     its #app-settings-page-actions slot, nav-bar style), so only an optional
	     description renders in the flow. Desktop keeps the frappe-ui dialog
	     header untouched. -->
	<template v-if="mobilePage">
		<!-- defer: the settings sub-page slides in as one freshly-mounted layer, so
		     the bar's teleport target isn't in the document yet while this header
		     mounts — a non-deferred Teleport fails and breaks the whole page. -->
		<Teleport defer to="#app-settings-page-actions">
			<slot name="actions" />
		</Teleport>
		<div v-if="$slots.default || $attrs.description" class="shrink-0 px-4 pt-4">
			<slot>
				<p class="text-ink-gray-6 min-w-0 text-base">{{ $attrs.description }}</p>
			</slot>
		</div>
	</template>
	<SettingsHeader v-else v-bind="$attrs">
		<template v-if="$slots.default" #default>
			<slot />
		</template>
		<template v-if="$slots.actions" #actions>
			<slot name="actions" />
		</template>
	</SettingsHeader>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { SettingsHeader } from 'frappe-ui'

defineOptions({ inheritAttrs: false })

const mobilePage = inject('app-settings-mobile-page', false)
</script>
