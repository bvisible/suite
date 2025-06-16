<template>
	<CollapsibleSection title="Style" :initialState="true">
		<template #default>
			<Select
				:options="presetTextStyles"
				:modelValue="activeElement.defaultStyle || 'body'"
				@update:modelValue="applyPresetTextStyles"
			/>

			<div class="grid grid-cols-5 gap-2">
				<button
					v-for="style in styleProperties"
					:key="style.property"
					:class="getFontStyleButtonClasses(style.property, style.value)"
					@click="toggleTextProperty(style.property, style.value)"
				>
					<component
						:is="style.icon"
						size="16"
						:strokeWidth="1.5"
						:class="getFontStyleIconClasses(style.property, style.value)"
					/>
				</button>
			</div>

			<div
				class="h-8 rounded-[10px] bg-gray-100 w-full flex items-center justify-between p-0.5 border"
			>
				<div
					v-for="textAlign in textAlignProperties"
					:key="textAlign.alignValue"
					:class="getTabClasses(textAlign.alignValue)"
					@click="activeElement.textAlign = textAlign.alignValue"
				>
					<component
						:is="textAlign.icon"
						size="16"
						:class="getAlignIconClasses(textAlign.alignValue)"
					/>
				</div>
			</div>
		</template>
	</CollapsibleSection>

	<CollapsibleSection title="Font" :initialState="true">
		<template #default>
			<FormControl
				type="autocomplete"
				:options="textFonts"
				size="sm"
				variant="subtle"
				:modelValue="activeElement.fontFamily"
				@update:modelValue="(font) => (activeElement.fontFamily = font.value)"
			/>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Size</div>
				<div class="w-28">
					<NumberInput
						v-model="activeElement.fontSize"
						suffix="px"
						:rangeStart="5"
						:rangeEnd="100"
						:rangeStep="1"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Color</div>
				<ColorPicker v-model="activeElement.color" />
			</div>
		</template>
	</CollapsibleSection>

	<CollapsibleSection title="Spacing">
		<template #default>
			<SliderInput
				label="Line Height"
				:rangeStart="0.1"
				:rangeEnd="5.0"
				:rangeStep="0.1"
				:modelValue="parseFloat(activeElement.lineHeight)"
				@update:modelValue="(value) => (activeElement.lineHeight = value)"
			/>

			<SliderInput
				label="Letter Spacing"
				:rangeStart="-10"
				:rangeEnd="50"
				:rangeStep="0.1"
				:modelValue="parseFloat(activeElement.letterSpacing)"
				@update:modelValue="(value) => (activeElement.letterSpacing = value)"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { computed } from 'vue'
import { FormControl, Select } from 'frappe-ui'
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

import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { slide } from '@/stores/slide'
import {
	activeElementIds,
	focusElementId,
	toggleTextProperty,
	activeElement,
} from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

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

const textAlignProperties = [
	{
		alignValue: 'left',
		icon: AlignLeft,
	},
	{
		alignValue: 'center',
		icon: AlignCenter,
	},
	{
		alignValue: 'right',
		icon: AlignRight,
	},
	{
		alignValue: 'justify',
		icon: AlignJustify,
	},
]

const presetTextStyles = [
	{ label: 'Title', value: 'title' },
	{ label: 'Subtitle', value: 'subtitle' },
	{ label: 'Body', value: 'body' },
]

const applyPresetTextStyles = (textStyle) => {
	if (textStyle === 'title') {
		activeElement.value.fontWeight = 'bold'
		activeElement.value.fontSize = 60
		activeElement.value.lineHeight = 1.5
	} else if (textStyle === 'subtitle') {
		activeElement.value.fontWeight = 'bold'
		activeElement.value.fontSize = 30
		activeElement.value.lineHeight = 1.2
	} else if (textStyle === 'body') {
		activeElement.value.fontWeight = 'normal'
		activeElement.value.fontSize = 20
		activeElement.value.lineHeight = 1
	}
	activeElement.value.defaultStyle = textStyle
}

const getFontStyleButtonClasses = (property, value) => {
	const baseClasses = 'cursor-pointer rounded flex items-center justify-center py-1.5'
	if (activeElement.value[property]?.includes(value)) {
		return `${baseClasses} bg-gray-100`
	}
	return baseClasses
}

const getFontStyleIconClasses = (property, value) => {
	return activeElement.value[property]?.includes(value) ? 'text-gray-900' : 'text-gray-700'
}

const getTabClasses = (alignValue) => {
	const baseClasses = 'rounded h-full flex items-center justify-center px-4 cursor-pointer'
	if (activeElement.value.textAlign === alignValue) {
		return `${baseClasses} bg-white shadow`
	}
	return baseClasses
}

const getAlignIconClasses = (alignValue) => {
	const baseClasses = 'stroke-[1.5] text-gray-600'
	if (activeElement.value.textAlign === alignValue) {
		return `${baseClasses} text-gray-800`
	}
	return baseClasses
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
