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
import { FrappeUIProvider } from 'frappe-ui'
</script>
