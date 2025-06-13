<template>
	<CollapsibleSection title="Style" :initialState="true">
		<template #default>
			<Select
				:options="presetTextStyles"
				:modelValue="activeElement.defaultStyle || 'body'"
				@update:modelValue="applyPresetTextStyles"
			/>

			<div class="flex items-center justify-between">
				<button
					v-for="style in styleProperties"
					:key="style.property"
					class="cursor-pointer rounded-sm p-1.5"
					:class="
						activeElement[style.property]?.includes(style.value) ? 'bg-gray-200' : ''
					"
					@click="toggleTextProperty(style.property, style.value)"
				>
					<component :is="style.icon" size="18" :strokeWidth="1.5" />
				</button>
			</div>

			<div class="flex items-center justify-between">
				<button
					v-for="textAlign in ['left', 'center', 'right', 'justify']"
					class="cursor-pointer rounded-sm p-1.5"
					:class="activeElement.textAlign == textAlign ? 'bg-gray-200' : ''"
					@click="activeElement.textAlign = textAlign"
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
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
