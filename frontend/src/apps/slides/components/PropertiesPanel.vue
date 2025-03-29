<template>
	<div
		class="fixed right-0 z-20 flex flex-col h-[94.35%] w-64 bg-white border-l shadow-[0_10px_24px_-3px_rgba(199,199,199,0.6)]"
		@wheel.prevent
	>
		<SlideProperties v-if="activeTab == 'slide'" />

		<TextProperties v-else-if="activeTab == 'text'" />

		<ImageProperties v-else-if="activeTab == 'image'" />

		<VideoProperties v-else-if="activeTab == 'video'" />

		<div v-else>
			<div v-if="activeElement && activeTab != 'video'" :class="sectionClasses">
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
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { FormControl } from 'frappe-ui'
import { FlipHorizontal, FlipVertical, Repeat2, TvMinimalPlay, Ban } from 'lucide-vue-next'

import SlideProperties from './SlideProperties.vue'
import TextProperties from '@/components/TextProperties.vue'
import ImageProperties from './ImageProperties.vue'
import VideoProperties from './VideoProperties.vue'

import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from './controls/CollapsibleSection.vue'

import { presentation } from '@/stores/presentation'
import { slide, slideIndex } from '@/stores/slide'
import { activeElement } from '@/stores/element'

const activeTab = computed(() => {
	if (activeElement.value) return activeElement.value.type
	return 'slide'
})

const sectionClasses = 'flex flex-col gap-4 p-4 border-b'
const sectionTitleClasses = 'text-2xs font-semibold uppercase text-gray-700'
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
