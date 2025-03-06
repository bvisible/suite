<template>
	<div>
		<router-view />
		<Toaster richColors expand :visibleToasts="2" />
	</div>
</template>

<script setup>
import { Toaster } from 'vue-sonner'
</script>
