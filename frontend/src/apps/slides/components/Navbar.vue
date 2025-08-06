<template>
	<div
		class="relative z-10 flex items-center justify-between border-b bg-white p-2"
		@wheel.prevent
	>
		<router-link class="flex items-center gap-2" :to="{ name: 'Home' }">
			<img src="/slides-logo.svg" class="h-7" />
			<div class="text-base font-semibold">Slides</div>
		</router-link>

		<slot></slot>

		<div class="flex items-center justify-end gap-2">
			<slot name="actions"></slot>
			<Button variant="solid" :label="primaryButton.label" @click="primaryButton.onClick">
				<template #prefix>
					<component :is="primaryButton.icon" size="14" class="stroke-[1.5] text-white" />
				</template>
			</Button>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	primaryButton: Object,
})
</script>
