<template>
	<div :class="sectionClasses">
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<div :class="sectionTitleClasses">Slide</div>
				<div class="pe-0.5 text-2xs font-semibold text-gray-700">
					{{ slideIndex + 1 + ' of ' + slides.length }}
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Template Layout</div>
				<div
					class="cursor-pointer pe-1 text-gray-500 hover:text-gray-600"
					@click="$emit('openLayoutDialog')"
				>
					<LucidePenLine class="size-4" :strokeWidth="1.5" />
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Background Color</div>
				<ColorPicker v-model="currentSlide.background" />
			</div>
		</div>
	</div>

	<CollapsibleSection title="Transition">
		<template #default>
			<Select
				:options="['Slide In', 'Fade', 'None']"
				:modelValue="currentSlide.transition"
				@update:modelValue="(option) => setSlideTransition(option)"
			/>

			<SliderInput
				v-show="currentSlide.transition && currentSlide.transition != 'None'"
				label="Duration"
				:rangeStart="0"
				:rangeEnd="4"
				:rangeStep="0.1"
				:modelValue="parseFloat(currentSlide.transitionDuration)"
				@update:modelValue="(value) => setTransitionDuration(value)"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { Select } from 'frappe-ui'

import { slides, slideIndex, currentSlide } from '@/stores/slide'
import { sectionClasses, sectionTitleClasses, fieldLabelClasses } from '@/utils/constants'

import SliderInput from '@/components/controls/SliderInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

const emit = defineEmits(['openLayoutDialog'])

const setSlideTransition = (option) => {
	currentSlide.value.transition = option
	if (option == 'None') currentSlide.value.transitionDuration = 0
	else currentSlide.value.transitionDuration = 1
}

const setTransitionDuration = (value) => {
	currentSlide.value.transitionDuration = value
}
</script>
