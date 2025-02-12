<template>
	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Style</div>
		<div class="flex items-center justify-between">
			<button
				v-for="style in styleProperties"
				:key="style.property"
				class="cursor-pointer rounded-sm p-1"
				:class="
					activeElements[0][style.property]?.includes(style.value) ? 'bg-gray-200' : ''
				"
				@click="toggleProperty(style.property, style.value)"
			>
				<component :is="style.icon" size="18" :strokeWidth="1.5" />
			</button>
		</div>

		<div class="flex items-center justify-between">
			<button
				v-for="textAlign in ['left', 'center', 'right', 'justify']"
				class="cursor-pointer rounded-sm p-1"
				:class="activeElements[0].textAlign == textAlign ? 'bg-gray-200' : ''"
				@click="activeElements[0].textAlign = textAlign"
			>
				<FeatherIcon :name="`align-${textAlign}`" class="h-4.5" />
			</button>
			<button class="cursor-pointer rounded-sm p-1">
				<FeatherIcon name="list" class="h-4.5" />
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
			:modelValue="activeElements[0].fontFamily"
			@update:modelValue="(font) => (activeElements[0].fontFamily = font.value)"
		/>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-600">Size</div>
			<div class="h-[30px] w-28">
				<NumberInput
					v-model="activeElements[0].fontSize"
					suffix="px"
					:rangeStart="5"
					:rangeEnd="100"
					:rangeStep="1"
				/>
			</div>
		</div>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-600">Colour</div>
			<ColorPicker v-model="activeElements[0].color" />
		</div>
	</div>

	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Spacing</div>

		<SliderInput
			label="Line Height"
			:rangeStart="0.1"
			:rangeEnd="5.0"
			:rangeStep="0.1"
			:modelValue="parseFloat(activeElements[0].lineHeight)"
			@update:modelValue="(value) => (activeElements[0].lineHeight = value)"
		/>

		<SliderInput
			label="Letter Spacing"
			:rangeStart="-10"
			:rangeEnd="50"
			:rangeStep="0.1"
			:modelValue="parseFloat(activeElements[0].letterSpacing)"
			@update:modelValue="(value) => (activeElements[0].letterSpacing = value)"
		/>
	</div>
</template>

<script setup>
import { FormControl } from 'frappe-ui'
import { Bold, Italic, Underline, Strikethrough, CaseUpper } from 'lucide-vue-next'

import SliderInput from './controls/SliderInput.vue'
import NumberInput from './controls/NumberInput.vue'
import ColorPicker from './controls/ColorPicker.vue'

import { slide } from '@/stores/slide'
import { activeElementIds, activeElements } from '@/stores/element'
import { debounce } from '@/utils/helpers'

const sectionClasses = 'flex flex-col gap-4 border-b p-4'
const sectionTitleClasses = 'text-2xs font-semibold uppercase text-gray-700'

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

const toggleProperty = (property, value) => {
	const oldStyle = activeElements.value[0][property]
	let newStyle = ''

	switch (property) {
		case 'fontWeight':
			newStyle = oldStyle == 'bold' ? 'normal' : 'bold'
			break
		case 'fontStyle':
			newStyle = oldStyle == 'italic' ? 'normal' : 'italic'
			break
		case 'textTransform':
			newStyle = oldStyle == 'uppercase' ? 'none' : 'uppercase'
			break
		default:
			if (!oldStyle) {
				newStyle = value
				break
			}
			newStyle = oldStyle.includes(value)
				? oldStyle.replace(value, '')
				: oldStyle + ' ' + value
	}
	slide.value.elements[activeElementIds.value[0]][property] = newStyle
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
