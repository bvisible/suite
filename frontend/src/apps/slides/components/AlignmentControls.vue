<template>
	<CollapsibleSection title="Alignment" :initialState="true">
		<template #default>
			<div class="flex items-center gap-3">
				<NumberInput
					v-model="selectionBounds.left"
					prefix="x"
					:rangeStart="0"
					:rangeStep="1"
					:hideButtons="true"
				/>
				<NumberInput
					v-model="selectionBounds.top"
					prefix="y"
					:rangeStart="0"
					:rangeStep="1"
					:hideButtons="true"
				/>
			</div>

			<div v-for="axis in axes" :key="axis" class="flex flex-col gap-1.5">
				<div :class="fieldLabelClasses">{{ axis.label }}</div>
				<div class="grid grid-cols-3 gap-3">
					<div
						v-for="option in axis.options"
						:key="option.direction"
						:class="getAlignmentButtonClasses(option.direction)"
						@click="performAlignment(option.direction)"
						@mouseenter="updateGuideVisibilityMap(option.guide, true)"
						@mouseleave="updateGuideVisibilityMap(option.guide, false)"
					>
						<component :is="option.icon" size="18" :strokeWidth="1.5" />
					</div>
				</div>
			</div>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { computed } from 'vue'

import {
	AlignStartVertical,
	AlignCenterVertical,
	AlignEndVertical,
	AlignStartHorizontal,
	AlignCenterHorizontal,
	AlignEndHorizontal,
} from 'lucide-vue-next'

import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { slideBounds, selectionBounds, guideVisibilityMap } from '@/stores/slide'
import { fieldLabelClasses } from '@/utils/constants'

const horizontalAlignmentOptions = [
	{
		direction: 'left',
		guide: 'leftEdge',
		icon: AlignStartVertical,
	},
	{
		direction: 'centerY',
		guide: 'centerY',
		icon: AlignCenterVertical,
	},
	{
		direction: 'right',
		guide: 'rightEdge',
		icon: AlignEndVertical,
	},
]

const verticalAlignmentOptions = [
	{
		direction: 'top',
		guide: 'topEdge',
		icon: AlignStartHorizontal,
	},
	{
		direction: 'centerX',
		guide: 'centerX',
		icon: AlignCenterHorizontal,
	},
	{
		direction: 'bottom',
		guide: 'bottomEdge',
		icon: AlignEndHorizontal,
	},
]

const axes = [
	{
		label: 'Horizontal',
		options: horizontalAlignmentOptions,
	},
	{
		label: 'Vertical',
		options: verticalAlignmentOptions,
	},
]

const alignmentPositions = computed(() => {
	const slideWidth = slideBounds.width / slideBounds.scale
	const slideHeight = slideBounds.height / slideBounds.scale

	const { width: selectionWidth, height: selectionHeight } = selectionBounds

	return {
		left: 0,
		centerY: (slideWidth - selectionWidth) / 2,
		right: Math.round(slideWidth) - Math.round(selectionWidth),
		top: 0,
		centerX: Math.round(slideHeight / 2) - Math.round(selectionHeight / 2),
		bottom: Math.round(slideHeight) - Math.round(selectionHeight),
	}
})

const isAligned = (direction) => {
	const axis = ['left', 'centerY', 'right'].includes(direction) ? 'X' : 'Y'

	const expectedPos = Math.round(alignmentPositions.value[direction] * 100) / 100

	const currentPos =
		axis == 'X'
			? Math.round(selectionBounds.left * 100) / 100
			: Math.round(selectionBounds.top * 100) / 100

	return expectedPos == currentPos
}

const getAlignmentButtonClasses = (direction) => {
	const baseClasses =
		'flex cursor-pointer items-center justify-center rounded border py-1.5 hover:border-gray-400'

	const activeClasses = isAligned(direction)
		? 'border-gray-500 text-gray-900'
		: 'text-gray-600 hover:text-gray-700'

	return `${baseClasses} ${activeClasses}`
}

const alignHorizontally = (direction) => {
	selectionBounds.left = Math.round(alignmentPositions.value[direction])
}

const alignVertically = (direction) => {
	selectionBounds.top = Math.round(alignmentPositions.value[direction])
}

const performAlignment = (direction) => {
	switch (direction) {
		case 'left':
		case 'centerY':
		case 'right':
			alignHorizontally(direction)
			break
		default:
			// 'top', 'centerY', 'bottom'
			alignVertically(direction)
			break
	}
}

const updateGuideVisibilityMap = (direction, value) => {
	guideVisibilityMap[direction] = value
}
</script>
