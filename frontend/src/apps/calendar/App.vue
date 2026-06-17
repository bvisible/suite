<script setup lang="ts">
import { onMounted, onUnmounted, watchEffect } from 'vue'
import { FrappeUIProvider, createResource } from 'frappe-ui'

import { raiseToast, shouldIgnoreKeypress } from '@/utils'
import { useTheme } from '@/utils/composables'
import { userStore } from '@/stores/user'

const { userResource } = userStore()
const { dataTheme } = useTheme()

watchEffect(() => document.documentElement.setAttribute('data-theme', dataTheme.value))

onMounted(() => window.addEventListener('keydown', handleKeyDown))
onUnmounted(() => window.removeEventListener('keydown', handleKeyDown))

const handleKeyDown = (e: KeyboardEvent) => {
	const key = e.key.toLowerCase()

	// Handle Ctrl/Cmd+Shift+L (Cycle Theme)
	if ((e.metaKey || e.ctrlKey) && e.shiftKey && key === 'l' && !shouldIgnoreKeypress(e, true)) {
		e.preventDefault()
		return cycleTheme()
	}
}

const COLOR_SCHEME_CYCLE = ['System Default', 'Light Mode', 'Dark Mode'] as const

const cycleTheme = () => {
	const current = userResource.data?.color_scheme
	if (!current) return

	const idx = COLOR_SCHEME_CYCLE.indexOf(current)
	const next = COLOR_SCHEME_CYCLE[(idx + 1) % COLOR_SCHEME_CYCLE.length]
	updateColorScheme.submit(next)
}

const updateColorScheme = createResource({
	url: 'frappe.client.set_value',
	makeParams: (color_scheme) => ({
		doctype: 'User Settings',
		name: userResource.data.user_settings,
		fieldname: { color_scheme },
	}),
	onSuccess: (data) => {
		raiseToast(__('Color scheme updated to {0}.', [data.color_scheme]))
		userResource.reload()
	},
})
</script>

<template>
	<FrappeUIProvider>
		<router-view />
	</FrappeUIProvider>
</template>
