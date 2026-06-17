<template>
	<CollapsibleSection title="Border">
		<template #default>
			<div
				class="flex h-8 w-full items-center justify-between rounded-[10px] border bg-gray-50 p-0.5"
			>
				<div
					v-for="(style, index) in borderStyles"
					:key="index"
					:class="getTabClasses(style)"
					@click="addBorder(style)"
				>
					<LucideBan v-if="style == 'none'" :class="getTabIconClasses(style)" />
					<div
						v-else
						:class="getTabIconClasses(style)"
						:style="{ borderStyle: style }"
					></div>
				</div>
			</div>

			<div v-if="activeElement.borderStyle != 'none'" class="flex flex-col gap-3">
				<div class="flex items-center justify-between">
					<div :class="fieldLabelClasses">Width</div>
					<div class="w-28">
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
					<div :class="fieldLabelClasses">Radius</div>
					<div class="w-28">
						<NumberInput
							v-model="activeElement.borderRadius"
							suffix="px"
							:rangeStart="1"
							:rangeEnd="50"
						/>
					</div>
				</div>

				<div class="flex items-center justify-between">
					<div :class="fieldLabelClasses">Color</div>
					<ColorPicker
						v-model="activeElement.borderColor"
						@colordown="onBorderColorUpdateStart"
						@colorup="onBorderColorUpdateEnd"
					/>
				</div>
			</div>
		</template>
	</CollapsibleSection>

	<ShadowProperties />
</template>

<script setup>
import { inject } from 'vue'

import NumberInput from '@/apps/slides/components/controls/NumberInput.vue'
import ColorPicker from '@/apps/slides/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/apps/slides/components/controls/CollapsibleSection.vue'
import ShadowProperties from '@/apps/slides/components/ShadowProperties.vue'

import { activeElement } from '@/apps/slides/stores/element'
import { fieldLabelClasses } from '@/apps/slides/utils/constants'

const setPropertyDeferred = inject('setPropertyDeferred')

const borderStyles = ['none', 'solid', 'dashed', 'dotted']

const addBorder = (style) => {
	activeElement.value.borderStyle = style
	if (style != 'none') {
		activeElement.value.borderWidth = 0.5
		activeElement.value.borderColor = '#d2d2d2ff'
		activeElement.value.borderRadius = 10
	} else {
		activeElement.value.borderWidth = 0
		activeElement.value.borderColor = ''
		activeElement.value.borderRadius = 0
	}
}

const getTabClasses = (style) => {
	const baseClasses = 'flex h-full w-1/6 cursor-pointer items-center justify-center rounded'
	if (activeElement.value.borderStyle == style) {
		return `${baseClasses} bg-white shadow`
	}
	return baseClasses
}

const getTabIconClasses = (style) => {
	const isActive = activeElement.value.borderStyle == style
	if (style == 'none') {
		return `size-4 ${isActive ? 'text-gray-800' : 'text-gray-500'}`
	} else {
		return `h-4 w-5 rounded-sm border ${isActive ? 'border-gray-800' : 'border-gray-500'}`
	}
}

const { onStart: onBorderColorUpdateStart, onEnd: onBorderColorUpdateEnd } = setPropertyDeferred(
	'element',
	'borderColor',
)
</script>
