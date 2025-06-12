<template>
	<FrappeUIProvider>
		<Layout>
			<router-view />
		</Layout>
		<Dialogs />
	</FrappeUIProvider>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { FrappeUIProvider } from 'frappe-ui'

import { Dialogs } from '@/utils/dialogs'
import DefaultLayout from '@/components/DefaultLayout.vue'
import EmptyLayout from '@/components/EmptyLayout.vue'
import LoginLayout from '@/components/LoginLayout.vue'

const route = useRoute()

const Layout = computed(() => {
	if (route.meta.isLogin || route.meta.isSetup) return LoginLayout
	if (route.meta.isMimeMessage) return EmptyLayout
	return DefaultLayout
})
</script>
