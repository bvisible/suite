<template>
	<div
		class="flex h-full w-64 flex-col overflow-y-auto border-l bg-white pb-14 custom-scrollbar"
		@wheel="handleScrollBarWheelEvent"
	>
		<div v-if="activeElementIds.length">
			<AlignmentControls />
			<PlacementProperties />
			<component :is="activeProperties" />
			<AppearanceProperties v-if="activeElement" />
		</div>
		<SlideProperties v-else-if="currentSlide" />
	</div>
</template>

<script setup>
import { computed, inject, provide } from 'vue'

import SlideProperties from '@/components/SlideProperties.vue'
import TextProperties from '@/components/TextProperties.vue'
import ImageProperties from '@/components/ImageProperties.vue'
import VideoProperties from '@/components/VideoProperties.vue'
import AlignmentControls from '@/components/AlignmentControls.vue'
import PlacementProperties from '@/components/PlacementProperties.vue'
import AppearanceProperties from '@/components/AppearanceProperties.vue'

import { currentSlide } from '@/stores/slide'
import { activeElement, activeElementIds } from '@/stores/element'
import { handleScrollBarWheelEvent } from '@/utils/helpers'
import { editElementCommand } from '@/stores/commands'

const activeProperties = computed(() => {
	const elementType = activeElement.value?.type

	switch (elementType) {
		case 'text':
			return TextProperties
		case 'image':
			return ImageProperties
		case 'video':
			return VideoProperties
	}
})

const commandHistory = inject('commandHistory')

const setProperty = (property, value) => {
	const oldValue = activeElement.value[property]
	commandHistory.execute(
		editElementCommand({
			slideId: currentSlide.value.name,
			elementIds: activeElementIds.value,
			property,
			oldValue,
			newValue: value,
		}),
	)
}

provide('setProperty', setProperty)
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
