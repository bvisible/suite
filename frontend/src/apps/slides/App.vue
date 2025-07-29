<template>
	<FrappeUIProvider>
		<router-view v-slot="{ Component }">
			<keep-alive :max="5">
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</FrappeUIProvider>
	<Toaster richColors expand :visibleToasts="2" />
</template>

<script setup>
import { Toaster } from 'vue-sonner'
import { FrappeUIProvider } from 'frappe-ui'
</script>
