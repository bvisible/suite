<template>
	<div
		class="z-10 flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-300"
		@wheel.prevent
	>
		<router-link class="flex items-center gap-2" :to="{ name: 'Home' }">
			<img src="../icons/slides.svg" class="h-7" />
			<div class="text-base font-semibold">Slides</div>
		</router-link>

		<slot></slot>

		<div class="flex items-center gap-2 justify-end">
			<slot name="actions"></slot>
			<Button variant="solid" :label="primaryButton.label" @click="primaryButton.onClick">
				<template #prefix>
					<component :is="primaryButton.icon" size="14" class="text-white stroke-[1.5]" />
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
