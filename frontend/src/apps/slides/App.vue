<template>
	<div>
		<FrappeUIProvider>
			<router-view />
		</FrappeUIProvider>
		<Toaster richColors expand :visibleToasts="2" />
	</div>
</template>

<script setup>
import { Toaster } from 'vue-sonner'
import { FrappeUIProvider } from 'frappe-ui'
</script>
