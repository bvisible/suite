<template>
	<div
		class="flex h-full w-64 flex-col overflow-y-auto border-l bg-white pb-14 custom-scrollbar"
		@wheel="handleScrollBarWheelEvent"
	>
		<div v-if="!activeElement">
			<SlideProperties v-if="currentSlide" @openLayoutDialog="$emit('openLayoutDialog')" />
		</div>
		<div v-else>
			<component :is="activeProperties" />
		</div>

		<div v-if="activeElementIds.length">
			<AppearanceProperties v-if="activeElement" />
			<AlignmentControls />
			<PlacementProperties />
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

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

const emit = defineEmits(['openLayoutDialog'])

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
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
