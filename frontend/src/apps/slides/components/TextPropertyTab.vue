<template>
	<div class="flex flex-col gap-4 border-b px-4 py-4">
		<div class="text-2xs font-semibold uppercase text-gray-700">Style</div>
		<div class="flex items-center justify-between">
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.fontWeight == 'bold' ? 'bg-gray-200' : ''"
				@click="toggleProperty('fontWeight')"
			>
				<FeatherIcon name="bold" class="h-4" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.fontStyle == 'italic' ? 'bg-gray-200' : ''"
				@click="toggleProperty('fontStyle')"
			>
				<FeatherIcon name="italic" class="h-4" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textDecoration?.includes('underline') ? 'bg-gray-200' : ''"
				@click="toggleProperty('textDecoration', 'underline')"
			>
				<FeatherIcon name="underline" class="h-4" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textDecoration?.includes('line-through') ? 'bg-gray-200' : ''"
				@click="toggleProperty('textDecoration', 'line-through')"
			>
				<Strikethrough size="16" :strokeWidth="1.5" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textTransform == 'uppercase' ? 'bg-gray-200' : ''"
				@click="toggleProperty('textTransform')"
			>
				<CaseUpper size="20" :strokeWidth="1.5" />
			</button>
		</div>

		<div class="flex items-center justify-between">
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textAlign == 'left' ? 'bg-gray-200' : ''"
				@click="activeElement.textAlign = 'left'"
			>
				<FeatherIcon name="align-left" class="h-4.5" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textAlign == 'center' ? 'bg-gray-200' : ''"
				@click="activeElement.textAlign = 'center'"
			>
				<FeatherIcon name="align-center" class="h-4.5" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textAlign == 'right' ? 'bg-gray-200' : ''"
				@click="activeElement.textAlign = 'right'"
			>
				<FeatherIcon name="align-right" class="h-4.5" />
			</button>
			<button
				class="cursor-pointer rounded-sm p-1"
				:class="activeElement.textAlign == 'justify' ? 'bg-gray-200' : ''"
				@click="activeElement.textAlign = 'justify'"
			>
				<FeatherIcon name="align-justify" class="h-4.5" />
			</button>
			<button class="cursor-pointer rounded-sm p-1">
				<FeatherIcon name="list" class="h-4.5" />
			</button>
		</div>
	</div>

	<div class="flex flex-col gap-4 border-b px-4 py-4">
		<div class="text-2xs font-semibold uppercase text-gray-700">Font</div>
		<FormControl
			type="autocomplete"
			:options="textFonts"
			size="sm"
			variant="subtle"
			:modelValue="activeElement.fontFamily"
			@update:modelValue="(font) => (activeElement.fontFamily = font.value)"
		/>

		<div class="flex items-center justify-between">
			<div class="text-sm text-gray-600">Size</div>
			<div class="h-[30px] w-28">
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
			<div class="text-sm text-gray-600">Colour</div>
			<ColorPicker v-model="activeElement.color" />
		</div>
	</div>

	<div class="flex flex-col gap-4 border-b px-4 py-4">
		<div class="text-2xs font-semibold uppercase text-gray-700">Spacing</div>

		<SliderInput
			label="Line Height"
			v-model="activeElement.lineHeight"
			:rangeStart="0.1"
			:rangeEnd="5.0"
			:rangeStep="0.1"
		/>

		<SliderInput
			label="Letter Spacing"
			v-model="activeElement.letterSpacing"
			:rangeStart="-10"
			:rangeEnd="50"
			:rangeStep="0.1"
		/>
	</div>
</template>

<script setup>
import { FormControl } from 'frappe-ui'
import { Strikethrough, CaseUpper } from 'lucide-vue-next'

import { debounce } from '@/utils/debounce'
import { activeElement } from '@/stores/element'
import SliderInput from './SliderInput.vue'
import NumberInput from './NumberInput.vue'
import ColorPicker from './ColorPicker.vue'

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

const styleProps = ['fontSize', 'fontWeight', 'fontFamily', 'fontStyle', 'textDecoration']

const toggleProperty = (property, textDecoration) => {
	let oldStyle = activeElement.value[property]
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
				newStyle = textDecoration
				break
			}
			newStyle = oldStyle.includes(textDecoration)
				? oldStyle.replace(textDecoration, '')
				: oldStyle + ' ' + textDecoration
	}
	activeElement.value[property] = newStyle
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
