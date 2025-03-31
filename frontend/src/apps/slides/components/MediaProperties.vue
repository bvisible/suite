<template>
	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Border</div>

		<div
			class="flex h-8 w-full items-center gap-3 justify-between rounded border bg-gray-50 p-[2px] px-2"
		>
			<div
				v-for="(style, index) in borderStyles"
				:key="index"
				class="flex h-4/5 w-1/4 cursor-pointer items-center justify-center rounded-sm"
				:class="activeElement.borderStyle == style ? 'bg-white shadow' : ''"
				@click="addBorder(style)"
			>
				<LucideBan v-if="style == 'none'" class="h-4 w-4" />
				<div
					v-else
					class="h-4 w-5 rounded-sm border border-black"
					:style="{ borderStyle: style }"
				></div>
			</div>
		</div>

		<div v-if="activeElement.borderStyle != 'none'" class="flex flex-col gap-4">
			<div class="flex items-center justify-between">
				<div class="text-sm text-gray-600">Width</div>
				<div class="h-[30px] w-28">
					<NumberInput
						v-model="activeElement.borderWidth"
						suffix="px"
						:rangeStart="0"
						:rangeEnd="50"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div class="text-sm text-gray-600">Radius</div>
				<div class="h-[30px] w-28">
					<NumberInput
						v-model="activeElement.borderRadius"
						suffix="px"
						:rangeStart="1"
						:rangeEnd="50"
					/>
				</div>
			</div>

			<div class="flex items-center justify-between">
				<div class="text-sm text-gray-600">Colour</div>
				<ColorPicker v-model="activeElement.borderColor" />
			</div>
		</div>
	</div>

	<div :class="sectionClasses">
		<div :class="sectionTitleClasses">Shadow</div>

		<SliderInput
			label="Offset X"
			:rangeStart="-50"
			:rangeEnd="50"
			:modelValue="parseFloat(activeElement.shadowOffsetX) || 0"
			@update:modelValue="(value) => (activeElement.shadowOffsetX = value)"
		/>

		<SliderInput
			label="Offset Y"
			:rangeStart="-50"
			:rangeEnd="50"
			:modelValue="parseFloat(activeElement.shadowOffsetY) || 0"
			@update:modelValue="(value) => (activeElement.shadowOffsetY = value)"
		/>

		<div class="flex flex-col gap-1">
			<div class="text-sm text-gray-600">Spread</div>
			<div class="flex items-center justify-between">
				<SliderInput
					class="w-4/5"
					:rangeStart="1"
					:rangeEnd="500"
					:modelValue="parseFloat(activeElement.shadowSpread) || 50"
					@update:modelValue="(value) => (activeElement.shadowSpread = value)"
					:showInput="false"
				/>
				<ColorPicker class="w-10 justify-end" v-model="activeElement.shadowColor" />
			</div>
		</div>
	</div>
</template>

<script setup>
import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'

import { activeElement } from '@/stores/element'
import { sectionClasses, sectionTitleClasses } from '@/utils/constants'

const borderStyles = ['none', 'solid', 'dashed', 'dotted']

const addBorder = (style) => {
	activeElement.value.borderStyle = style
	if (style != 'none') activeElement.value.borderWidth = 1
}
</script>
