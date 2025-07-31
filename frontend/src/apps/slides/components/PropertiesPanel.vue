<template>
	<div
		v-if="presentation.data"
		class="flex h-full w-64 flex-col overflow-y-auto border-l bg-white pb-14 custom-scrollbar"
		@wheel="handleScrollBarWheelEvent"
	>
		<div v-if="!activeElement">
			<SlideProperties />
			<AlignmentControls v-if="activeElementIds.length" />
		</div>
		<div v-else>
			<AlignmentControls v-if="activeElementIds.length" />
			<component :is="activeProperties" />
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { FormControl } from 'frappe-ui'

import SlideProperties from '@/components/SlideProperties.vue'
import TextProperties from '@/components/TextProperties.vue'
import ImageProperties from '@/components/ImageProperties.vue'
import VideoProperties from '@/components/VideoProperties.vue'
import AlignmentControls from '@/components/AlignmentControls.vue'

import SliderInput from '@/components/controls/SliderInput.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { presentation } from '@/stores/presentation'
import { slide } from '@/stores/slide'
import { activeElement, activeElementIds } from '@/stores/element'
import { handleScrollBarWheelEvent } from '@/utils/helpers'

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
