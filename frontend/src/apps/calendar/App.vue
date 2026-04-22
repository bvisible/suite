<script setup lang="ts">
import { watchEffect } from 'vue'
import { FrappeUIProvider } from 'frappe-ui'

import { useTheme } from '@/utils/composables'

const { dataTheme } = useTheme()

watchEffect(() => document.documentElement.setAttribute('data-theme', dataTheme.value))
</script>

<template>
	<FrappeUIProvider>
		<router-view />
	</FrappeUIProvider>
</template>
