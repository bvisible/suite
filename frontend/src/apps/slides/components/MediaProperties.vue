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

	<CollapsibleSection title="Shadow">
		<template #default>
			<div class="flex items-center justify-between">
				<div :class="fieldLabelClasses">Color</div>
				<ColorPicker
					class="pe-[0.2px]"
					v-model="activeElement.shadowColor"
					@colordown="onShadowColorUpdateStart"
					@colorup="onShadowColorUpdateEnd"
				/>
			</div>

			<SliderInput
				label="Spread"
				:rangeStart="0"
				:rangeEnd="500"
				v-model="activeElement.shadowSpread"
				@sliderdown="onShadowSpreadUpdateStart"
				@sliderup="onShadowSpreadUpdateEnd"
			/>

			<SliderInput
				label="Offset X"
				:rangeStart="-50"
				:rangeEnd="50"
				v-model="activeElement.shadowOffsetX"
				@sliderdown="onShadowOffsetXUpdateStart"
				@sliderup="onShadowOffsetXUpdateEnd"
			/>

			<SliderInput
				label="Offset Y"
				:rangeStart="-50"
				:rangeEnd="50"
				v-model="activeElement.shadowOffsetY"
				@sliderdown="onShadowOffsetYUpdateStart"
				@sliderup="onShadowOffsetYUpdateEnd"
			/>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { inject } from 'vue'
import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { currentSlide } from '@/stores/slide'
import { activeElement } from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'

import { useDeferredCommit } from '@/composables/useDeferredCommit'
import { editElementCommand } from '@/stores/commands'

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

const { onStart: onBorderColorUpdateStart, onEnd: onBorderColorUpdateEnd } = useDeferredCommit(
	() => activeElement.value?.borderColor,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: [activeElement.value?.id],
			property: 'borderColor',
			oldValue,
			newValue,
		}),
)

const { onStart: onShadowColorUpdateStart, onEnd: onShadowColorUpdateEnd } = useDeferredCommit(
	() => activeElement.value?.shadowColor,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: [activeElement.value?.id],
			property: 'shadowColor',
			oldValue,
			newValue,
		}),
)

const { onStart: onShadowSpreadUpdateStart, onEnd: onShadowSpreadUpdateEnd } = useDeferredCommit(
	() => activeElement.value?.shadowSpread,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: [activeElement.value?.id],
			property: 'shadowSpread',
			oldValue,
			newValue,
		}),
)

const { onStart: onShadowOffsetXUpdateStart, onEnd: onShadowOffsetXUpdateEnd } = useDeferredCommit(
	() => activeElement.value?.shadowOffsetX,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: [activeElement.value?.id],
			property: 'shadowOffsetX',
			oldValue,
			newValue,
		}),
)

const { onStart: onShadowOffsetYUpdateStart, onEnd: onShadowOffsetYUpdateEnd } = useDeferredCommit(
	() => activeElement.value?.shadowOffsetY,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: [activeElement.value?.id],
			property: 'shadowOffsetY',
			oldValue,
			newValue,
		}),
)

const setProperty = inject('setProperty')
</script>
