<template>
	<div class="fixed inset-0 z-20 flex flex-col bg-white" :class="{ hidden: !show }">
		<div class="sticky top-0 flex items-center border-b px-3 py-2.5">
			<Button icon="x" variant="ghost" class="mr-2" @click="close" />
			<h2>{{ __('Send Mail') }}</h2>
		</div>
		<div class="px-3 py-2.5">
			<slot name="body-content" />
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, watch } from 'vue'
import { Button } from 'frappe-ui'

const show = defineModel<boolean>()

const close = () => {
	if (show.value) show.value = false
}

watch(show, (val) => {
	if (val) history.pushState(null, '')
})

onMounted(() => window.addEventListener('popstate', close))

onUnmounted(() => window.removeEventListener('popstate', close))
</script>
