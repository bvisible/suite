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
				:options="['Magic Move', 'Fade', 'Slide In', 'None']"
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
				@update:modelValue="(value) => setTransitionAttribute('transitionDuration', value)"
			/>

			<div
				class="flex items-center justify-between"
				v-if="currentSlide.transition == 'Magic Move'"
			>
				<div :class="fieldLabelClasses">Fade In Other Elements</div>

				<Checkbox
					size="sm"
					class="cursor-pointer px-1"
					:modelValue="currentSlide.fadeUnmatchedElements"
					@update:modelValue="(v) => setTransitionAttribute('fadeUnmatchedElements', v)"
				/>
			</div>

			<Button
				label="Apply To All Slides"
				variant="outline"
				class="text-sm"
				@click="applyTransitionToAllSlides"
			>
				<template #prefix>
					<LucideCheckCheck class="size-3.5 stroke-[1.5]" />
				</template>
			</Button>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { Select, Checkbox, toast } from 'frappe-ui'

import { slides, slideIndex, currentSlide } from '@/stores/slide'
import { sectionClasses, sectionTitleClasses, fieldLabelClasses } from '@/utils/constants'
import { createConnectionsForMagicMove } from '@/stores/transition'

import SliderInput from '@/components/controls/SliderInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

const emit = defineEmits(['openLayoutDialog'])

const setSlideTransition = (option) => {
	const slide = currentSlide.value

	slide.transition = option

	if (option == 'None') {
		slide.transitionDuration = 0
	} else {
		slide.transitionDuration = 1
	}

	if (option == 'Magic Move') createConnectionsForMagicMove(slideIndex.value)

	slide.fadeUnmatchedElements = option == 'Magic Move'
}

const setTransitionAttribute = (property, value) => {
	currentSlide.value[property] = value
}

const applyTransitionToAllSlides = () => {
	const sourceSlide = currentSlide.value

	slides.value.forEach((slide, index) => {
		if (index !== slideIndex.value) {
			slide.transition = sourceSlide.transition
			slide.transitionDuration = sourceSlide.transitionDuration
			slide.fadeUnmatchedElements = sourceSlide.fadeUnmatchedElements

			if (sourceSlide.transition == 'Magic Move') createConnectionsForMagicMove(index)
		}
	})

	toast.success('Applied transition to all slides')
}
</script>
