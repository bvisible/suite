<template>
	<CollapsibleSection title="Border" :initialState="true">
		<template #default>
			<div
				class="flex h-8 w-full items-center gap-3 justify-between rounded-[10px] border bg-gray-50 p-0.5"
			>
				<div
					v-for="(style, index) in borderStyles"
					:key="index"
					class="flex h-full w-1/4 cursor-pointer items-center justify-center rounded"
					:class="activeElement.borderStyle == style ? 'bg-white shadow' : ''"
					@click="addBorder(style)"
				>
					<LucideBan
						v-if="style == 'none'"
						class="h-4 w-4"
						:class="
							activeElement.borderStyle == style ? 'text-gray-800' : 'text-gray-500'
						"
					/>
					<div
						v-else
						class="h-4 w-5 rounded-sm border"
						:class="
							activeElement.borderStyle == style
								? 'border-gray-800'
								: 'border-gray-500'
						"
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
							:rangeStep="0.5"
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
					<div class="text-sm text-gray-600">Color</div>
					<ColorPicker v-model="activeElement.borderColor" />
				</div>
			</div>
		</template>
	</CollapsibleSection>

	<CollapsibleSection title="Shadow">
		<template #default>
			<div class="flex items-center justify-between">
				<div class="text-sm text-gray-600">Color</div>
				<ColorPicker class="pe-[0.2px]" v-model="activeElement.shadowColor" />
			</div>

			<SliderInput
				label="Offset X"
				:rangeStart="-50"
				:rangeEnd="50"
				:modelValue="parseFloat(activeElement.shadowOffsetX) || 10"
				@update:modelValue="(value) => (activeElement.shadowOffsetX = value)"
			/>

			<SliderInput
				label="Offset Y"
				:rangeStart="-50"
				:rangeEnd="50"
				:modelValue="parseFloat(activeElement.shadowOffsetY) || 10"
				@update:modelValue="(value) => (activeElement.shadowOffsetY = value)"
			/>

			<SliderInput
				label="Spread"
				:rangeStart="1"
				:rangeEnd="500"
				:modelValue="parseFloat(activeElement.shadowSpread) || 50"
				@update:modelValue="(value) => (activeElement.shadowSpread = value)"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { activeElement } from '@/stores/element'

const borderStyles = ['none', 'solid', 'dashed', 'dotted']

const addBorder = (style) => {
	activeElement.value.borderStyle = style
	if (style != 'none') {
		activeElement.value.borderWidth = 0.5
		activeElement.value.borderColor = 'hsl(0, 1%, 80%)'
		activeElement.value.borderRadius = 10
	} else {
		activeElement.value.borderWidth = 0
		activeElement.value.borderColor = ''
		activeElement.value.borderRadius = 0
	}
}
</script>
