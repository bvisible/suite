<template>
	<div :class="sectionClasses">
		<div class="flex flex-col gap-3">
			<div class="flex items-center justify-between">
				<div :class="sectionTitleClasses">Slide</div>
				<div class="pe-0.5 text-2xs font-semibold text-gray-700">
					{{ slideIndex + 1 + ' of ' + presentation.data.slides.length }}
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
				<ColorPicker v-model="slide.background" />
			</div>
		</div>
	</div>

	<CollapsibleSection title="Transition" :initialState="true">
		<template #default>
			<Select
				:options="['Slide In', 'Fade', 'None']"
				:modelValue="slide.transition || 'None'"
				@update:modelValue="(option) => setSlideTransition(option)"
			/>

			<SliderInput
				v-show="slide.transition && slide.transition != 'None'"
				label="Duration"
				:rangeStart="0"
				:rangeEnd="4"
				:rangeStep="0.1"
				:modelValue="parseFloat(slide.transitionDuration) || 0"
				@update:modelValue="(value) => setTransitionDuration(value)"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { Select } from 'frappe-ui'

import { presentation } from '@/stores/presentation'
import { slide, slideIndex } from '@/stores/slide'
import { sectionClasses, sectionTitleClasses, fieldLabelClasses } from '@/utils/constants'

import SliderInput from '@/components/controls/SliderInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

const emit = defineEmits(['openLayoutDialog'])

const setSlideTransition = (option) => {
	slide.value.transition = option
	if (option.value == 'None') slide.value.transitionDuration = 0
	else slide.value.transitionDuration = 1
}

const setTransitionDuration = (value) => {
	slide.value.transitionDuration = value
}
</script>
