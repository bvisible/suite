<template>
	<FrappeUIProvider>
		<Layout>
			<router-view />
		</Layout>
		<InstallPrompt v-if="isMobile" />
	</FrappeUIProvider>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'

import { useScreenSize } from '@/utils/composables'
import DefaultLayout from '@/components/DefaultLayout.vue'
import EmptyLayout from '@/components/EmptyLayout.vue'
import InstallPrompt from '@/components/InstallPrompt.vue'
import LoginLayout from '@/components/LoginLayout.vue'

const { isMobile } = useScreenSize()

const route = useRoute()

const Layout = computed(() => {
	if (route.meta.isLogin || route.meta.isSetup) return LoginLayout
	if (route.meta.isMimeMessage) return EmptyLayout
	return DefaultLayout
})
</script>
