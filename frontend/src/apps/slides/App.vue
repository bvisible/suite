<template>
	<FrappeUIProvider>
		<router-view v-slot="{ Component }" :key="$route.fullPath">
			<keep-alive :max="5">
				<component :is="Component" />
			</keep-alive>
		</router-view>
	</FrappeUIProvider>
</template>

<script setup>
import { FrappeUIProvider } from 'frappe-ui'
</script>
