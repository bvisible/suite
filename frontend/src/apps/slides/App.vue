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
import { onMounted, h, ref, provide } from 'vue'
import { FrappeUIProvider, toast } from 'frappe-ui'

import { Wifi, WifiOff } from 'lucide-vue-next'

const isOnline = ref(false)

onMounted(() => {
	isOnline.value = navigator?.onLine
	window.addEventListener('online', () => {
		isOnline.value = true
		toast.create({
			message: 'You are back online.',
			icon: h(Wifi, { color: 'white' }),
		})
	})

	window.addEventListener('offline', () => {
		isOnline.value = false
		toast.create({
			message: 'Lost internet connection.',
			icon: h(WifiOff, { color: 'white' }),
		})
	})
})

provide('isOnline', isOnline)
</script>
