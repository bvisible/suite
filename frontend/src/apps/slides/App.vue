<template>
	<FrappeUIProvider>
		<router-view v-slot="{ Component }">
			<keep-alive :max="5">
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</FrappeUIProvider>
</template>

<script setup>
import { onMounted, h } from 'vue'
import { FrappeUIProvider, toast } from 'frappe-ui'

import { Wifi, WifiOff } from 'lucide-vue-next'

onMounted(() => {
	window.addEventListener('online', () => {
		toast.create({
			message: 'You are back online.',
			icon: h(Wifi, { color: 'white' }),
		})
	})

	window.addEventListener('offline', () => {
		toast.create({
			message: 'Lost internet connection.',
			icon: h(WifiOff, { color: 'white' }),
		})
	})
})
</script>
