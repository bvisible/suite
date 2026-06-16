<template>
	<div
		class="flex h-full w-64 flex-col overflow-y-auto border-l bg-white pb-4 custom-scrollbar"
		@wheel="handleScrollBarWheelEvent"
	>
		<div v-if="activeElementIds.length">
			<AlignmentControls />
			<LayoutProperties />
			<component :is="activeProperties" />
			<AppearanceProperties v-if="activeElement" />
		</div>
		<SlideProperties v-else-if="currentSlide" />
	</div>
</template>

<script setup>
import { computed, provide } from 'vue'

import SlideProperties from '@/apps/slides/components/SlideProperties.vue'
import TextProperties from '@/apps/slides/components/TextProperties.vue'
import ImageProperties from '@/apps/slides/components/ImageProperties.vue'
import VideoProperties from '@/apps/slides/components/VideoProperties.vue'
import ShapeProperties from '@/apps/slides/components/ShapeProperties.vue'
import AlignmentControls from '@/apps/slides/components/AlignmentControls.vue'
import LayoutProperties from '@/apps/slides/components/LayoutProperties.vue'
import AppearanceProperties from '@/apps/slides/components/AppearanceProperties.vue'

import { useDeferredCommit } from '@/apps/slides/composables/useDeferredCommit'

import { currentSlide } from '@/apps/slides/stores/slide'
import { activeElement, activeElementIds } from '@/apps/slides/stores/element'
import { commandHistory } from '@/apps/slides/stores/historyMeta'
import { handleScrollBarWheelEvent } from '@/apps/slides/utils/helpers'
import { editElementCommand, editSlideCommand } from '@/apps/slides/stores/commands'

const activeProperties = computed(() => {
	const elementType = activeElement.value?.type

	switch (elementType) {
		case 'text':
			return TextProperties
		case 'image':
			return ImageProperties
		case 'video':
			return VideoProperties
		case 'shape':
			return ShapeProperties
	}
})

const setProperty = (property, value) => {
	const oldValue = activeElement.value[property]
	commandHistory.execute(
		editElementCommand({
			slideId: currentSlide.value.clientId,
			elementIds: activeElementIds.value,
			property,
			oldValue,
			newValue: value,
		}),
	)
}

const setPropertyDeferred = (level, property) => {
	if (level === 'element') {
		return useDeferredCommit(
			() => activeElement.value?.[property],
			(oldValue, newValue) =>
				editElementCommand({
					slideId: currentSlide.value?.clientId,
					elementIds: activeElementIds.value,
					property,
					oldValue,
					newValue,
				}),
		)
	} else if (level === 'slide') {
		return useDeferredCommit(
			() => currentSlide.value?.[property],
			(oldValue, newValue) =>
				editSlideCommand({
					slideId: currentSlide.value?.clientId,
					property,
					oldValue,
					newValue,
				}),
		)
	}
}

provide('setProperty', setProperty)
provide('setPropertyDeferred', setPropertyDeferred)
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
