<template>
	<Layout>
		<router-view />
	</Layout>
	<Dialogs />
	<Toast />
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Toast } from 'frappe-ui'

import { useScreenSize } from '@/utils/composables'
import { Dialogs } from '@/utils/dialogs'
import DesktopLayout from '@/components/DesktopLayout.vue'
import EmptyLayout from '@/components/EmptyLayout.vue'
import LoginLayout from '@/components/LoginLayout.vue'
import MobileLayout from '@/components/MobileLayout.vue'

const route = useRoute()
const { isMobile } = useScreenSize()

const Layout = computed(() => {
	if (route.meta.isLogin || route.meta.isSetup) return LoginLayout
	if (route.meta.isMimeMessage) return EmptyLayout
	if (isMobile.value) return MobileLayout
	return DesktopLayout
})
</script>
