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
					:class="getFontStyleButtonClasses(style.property)"
					@click="toggleMark(style.property)"
				>
					<component
						:is="style.icon"
						size="16"
						:strokeWidth="1.5"
						:class="getFontStyleIconClasses(style.property)"
					/>
				</button>
			</div>

			<div class="flex items-center justify-between">
				<div
					class="flex h-8 w-4/5 items-center justify-between rounded-[10px] border bg-gray-100 p-0.5"
				>
					<div
						v-for="textAlign in textAlignProperties"
						:key="textAlign.alignValue"
						:class="getTabClasses(textAlign.alignValue)"
						@click="updateProperty('textAlign', textAlign.alignValue)"
					>
						<component
							:is="textAlign.icon"
							size="16"
							:class="getAlignIconClasses(textAlign.alignValue)"
						/>
					</div>
				</div>

				<div :class="listButtonClasses" @click="updateProperty('list')">
					<component
						:is="editorStyles.orderedList ? ListOrdered : List"
						size="16"
						class="stroke-[1.5] text-gray-600"
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
				:modelValue="editorStyles.fontFamily"
				@update:modelValue="(font) => updateProperty('fontFamily', font.value)"
			/>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Size</div>
				<div class="w-28">
					<NumberInput
						:modelValue="editorStyles.fontSize"
						@update:modelValue="(value) => updateProperty('fontSize', value)"
						suffix="px"
						:rangeStart="5"
						:rangeEnd="100"
						:rangeStep="1"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Color</div>
				<ColorPicker
					:modelValue="editorStyles.color"
					@update:modelValue="(val) => updateProperty('color', val)"
				/>
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
				:modelValue="editorStyles.lineHeight"
				@update:modelValue="(value) => updateProperty('lineHeight', parseFloat(value))"
			/>

			<SliderInput
				label="Letter Spacing"
				:rangeStart="-10"
				:rangeEnd="50"
				:rangeStep="0.1"
				:modelValue="editorStyles.letterSpacing"
				@update:modelValue="(value) => updateProperty('letterSpacing', parseFloat(value))"
			/>
		</template>
	</CollapsibleSection>

	<CollapsibleSection title="Other">
		<template #default>
			<SliderInput
				label="Opacity"
				:rangeStart="0"
				:rangeEnd="100"
				:modelValue="editorStyles.opacity"
				@update:modelValue="(value) => updateProperty('opacity', parseFloat(value))"
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
	ListOrdered,
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
import { activeElementIds, focusElementId, activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

import { useTextEditor } from '@/composables/useTextEditor'

const { activeEditor, editorStyles, toggleMark, updateProperty } = useTextEditor()

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
		property: 'bold',
		icon: Bold,
	},
	{
		property: 'italic',
		icon: Italic,
	},
	{
		property: 'underline',
		icon: Underline,
	},
	{
		property: 'strike',
		icon: Strikethrough,
	},
	{
		property: 'uppercase',
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
	{
		label: 'Title',
		value: 'title',
		bold: true,
		fontSize: 60,
		lineHeight: 1.5,
		textAlign: 'center',
	},
	{
		label: 'Subtitle',
		value: 'subtitle',
		bold: true,
		fontSize: 40,
		lineHeight: 1,
		textAlign: 'center',
	},
	{
		label: 'Body',
		value: 'body',
		bold: false,
		fontSize: 20,
		lineHeight: 1.5,
		textAlign: 'justify',
	},
]

const applyPresetTextStyles = (textStyle) => {
	const presetStyles = presetTextStyles.find((style) => style.value == textStyle)

	activeEditor.value
		.chain()
		.focus()
		.selectAll()
		.setMark('textStyle', {
			fontFamily: 'Arial',
			fontSize: presetStyles.fontSize,
			lineHeight: presetStyles.lineHeight,
			letterSpacing: 0,
			opacity: 100,
		})
		.run()

	activeEditor.value.chain().focus().setTextAlign(presetStyles.textAlign).run()
	activeEditor.value.chain().focus().setBold(presetStyles.bold).run()

	activeElement.value.defaultStyle = textStyle
}

const listButtonClasses = computed(() => {
	const baseClasses =
		'ms-2.5 flex h-full w-1/6 cursor-pointer items-center justify-center rounded py-2'
	const isActive = editorStyles.bulletList || editorStyles.orderedList
	return `${baseClasses} ${isActive ? 'bg-gray-100 text-gray-800' : ''}`
})

const getFontStyleButtonClasses = (property) => {
	const baseClasses = 'cursor-pointer rounded flex items-center justify-center py-1.5'
	if (editorStyles[property]) {
		return `${baseClasses} bg-gray-100`
	}
	return baseClasses
}

const getFontStyleIconClasses = (property) => {
	return editorStyles[property] ? 'text-gray-900' : 'text-gray-700'
}

const getTabClasses = (alignValue) => {
	const baseClasses = 'rounded h-full flex items-center justify-center w-1/5 cursor-pointer'
	if (editorStyles.textAlign == alignValue) {
		return `${baseClasses} bg-white shadow`
	}
	return baseClasses
}

const getAlignIconClasses = (alignValue) => {
	const baseClasses = 'stroke-[1.5] text-gray-600'
	if (editorStyles.textAlign == alignValue) {
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
