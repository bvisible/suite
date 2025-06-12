<template>
	<div :class="sectionClasses">
		<div class="flex items-center justify-between">
			<div :class="sectionTitleClasses">Slide</div>
			<div class="text-2xs font-semibold text-gray-700">
				{{ slideIndex + 1 + ' of ' + presentation.data.slides.length }}
			</div>
		</div>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-600">Background Color</div>
			<ColorPicker v-model="slide.background" />
		</div>
	</div>

	<CollapsibleSection title="Transition" :initialState="true">
		<template #default>
			<FormControl
				type="autocomplete"
				:options="['Slide In', 'Fade', 'None']"
				size="sm"
				variant="subtle"
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
import { FormControl } from 'frappe-ui'

import { presentation } from '@/stores/presentation'
import { slide, slideIndex } from '@/stores/slide'
import { sectionClasses, sectionTitleClasses } from '@/utils/constants'

import SliderInput from '@/components/controls/SliderInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

const setSlideTransition = (option) => {
	slide.value.transition = option.value
	if (option.value == 'None') slide.value.transitionDuration = 0
	else slide.value.transitionDuration = 1
}

const setTransitionDuration = (value) => {
	slide.value.transitionDuration = value
}
</script>
