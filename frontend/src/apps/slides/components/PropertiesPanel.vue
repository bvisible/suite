<template>
	<div
		class="fixed right-0 z-20 flex flex-col h-full top-[2.5rem] w-64 bg-white border-l"
		@wheel.prevent
	>
		<component :is="activeProperties" />

		<div v-if="activeElement" :class="sectionClasses">
			<div :class="sectionTitleClasses">Other</div>
			<SliderInput
				label="Opacity"
				:rangeStart="0"
				:rangeEnd="100"
				:modelValue="parseFloat(activeElement.opacity) || 100"
				@update:modelValue="(value) => (activeElement.opacity = value)"
			/>
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

import SliderInput from '@/components/controls/SliderInput.vue'

import { presentation } from '@/stores/presentation'
import { slide } from '@/stores/slide'
import { activeElement } from '@/stores/element'
import { sectionClasses, sectionTitleClasses } from '@/utils/constants'

const activeProperties = computed(() => {
	const elementType = activeElement.value?.type

	if (!elementType) return SlideProperties

	if (elementType == 'text') return TextProperties
	if (elementType == 'image') return ImageProperties
	if (elementType == 'video') return VideoProperties
})
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
