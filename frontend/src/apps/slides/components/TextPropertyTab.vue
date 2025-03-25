<template>
	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Style</div>
		<div class="flex items-center justify-between">
			<button
				v-for="style in styleProperties"
				:key="style.property"
				class="cursor-pointer rounded-sm p-1"
				:class="element[style.property]?.includes(style.value) ? 'bg-gray-200' : ''"
				@click="toggleTextProperty(style.property, style.value)"
			>
				<component :is="style.icon" size="18" :strokeWidth="1.5" />
			</button>
		</div>

		<div class="flex items-center justify-between">
			<button
				v-for="textAlign in ['left', 'center', 'right', 'justify']"
				class="cursor-pointer rounded-sm p-1"
				:class="element.textAlign == textAlign ? 'bg-gray-200' : ''"
				@click="element.textAlign = textAlign"
			>
				<AlignLeft v-if="textAlign == 'left'" size="18" class="stroke-[1.5]" />
				<AlignCenter v-if="textAlign == 'center'" size="18" class="stroke-[1.5]" />
				<AlignRight v-if="textAlign == 'right'" size="18" class="stroke-[1.5]" />
				<AlignJustify v-if="textAlign == 'justify'" size="18" class="stroke-[1.5]" />
			</button>
			<button class="cursor-pointer rounded-sm p-1">
				<List size="18" class="stroke-[1.5]" />
			</button>
		</div>
	</div>

	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Font</div>
		<FormControl
			type="autocomplete"
			:options="textFonts"
			size="sm"
			variant="subtle"
			:modelValue="element.fontFamily"
			@update:modelValue="(font) => (element.fontFamily = font.value)"
		/>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-600">Size</div>
			<div class="h-[30px] w-28">
				<NumberInput
					v-model="element.fontSize"
					suffix="px"
					:rangeStart="5"
					:rangeEnd="100"
					:rangeStep="1"
				/>
			</div>
		</div>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-600">Colour</div>
			<ColorPicker v-model="element.color" />
		</div>
	</div>

	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Spacing</div>

		<SliderInput
			label="Line Height"
			:rangeStart="0.1"
			:rangeEnd="5.0"
			:rangeStep="0.1"
			:modelValue="parseFloat(element.lineHeight)"
			@update:modelValue="(value) => (element.lineHeight = value)"
		/>

		<SliderInput
			label="Letter Spacing"
			:rangeStart="-10"
			:rangeEnd="50"
			:rangeStep="0.1"
			:modelValue="parseFloat(element.letterSpacing)"
			@update:modelValue="(value) => (element.letterSpacing = value)"
		/>
	</div>
</template>

<script setup>
import { computed } from 'vue'
import { FormControl } from 'frappe-ui'
import {
	Bold,
	Italic,
	Underline,
	Strikethrough,
	CaseUpper,
	List,
	AlignLeft,
	AlignCenter,
	AlignRight,
	AlignJustify,
} from 'lucide-vue-next'

import SliderInput from './controls/SliderInput.vue'
import NumberInput from './controls/NumberInput.vue'
import ColorPicker from './controls/ColorPicker.vue'

import { slide } from '@/stores/slide'
import {
	activeElementIds,
	activeElements,
	focusElementId,
	toggleTextProperty,
} from '@/stores/element'

const sectionClasses = 'flex flex-col gap-4 border-b p-4'
const sectionTitleClasses = 'text-2xs font-semibold uppercase text-gray-700'

const element = computed(() => {
	if (focusElementId.value) {
		return slide.value.elements.find((element) => element.id === focusElementId.value)
	} else {
		return activeElements.value[0]
	}
})

const textFonts = [
	'Arial',
	'Arial Black',
	'Comic Sans MS',
	'Courier New',
	'Georgia',
	'Helvetica',
	'Impact',
	'Lucida Console',
	'Lucida Sans Unicode',
	'Palatino Linotype',
	'Tahoma',
	'Times New Roman',
	'Trebuchet MS',
	'Verdana',
	'Inter',
]

const styleProperties = [
	{
		property: 'fontWeight',
		value: 'bold',
		icon: Bold,
	},
	{
		property: 'fontStyle',
		value: 'italic',
		icon: Italic,
	},
	{
		property: 'textDecoration',
		value: 'underline',
		icon: Underline,
	},
	{
		property: 'textDecoration',
		value: 'line-through',
		icon: Strikethrough,
	},
	{
		property: 'textTransform',
		value: 'uppercase',
		icon: CaseUpper,
	},
]
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
