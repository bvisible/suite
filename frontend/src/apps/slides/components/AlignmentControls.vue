<template>
	<CollapsibleSection title="Alignment" :initialState="activeElementIds?.length > 1">
		<template #default>
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
import { updatePosition, activeElementIds } from '@/stores/element'

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
		right: slideWidth - selectionWidth,
		top: 0,
		centerX: (slideHeight - selectionHeight) / 2,
		bottom: slideHeight - selectionHeight,
	}
})

const isAligned = (direction) => {
	const axis = ['left', 'centerY', 'right'].includes(direction) ? 'X' : 'Y'

	const expectedPos = Math.round(alignmentPositions.value[direction])

	const currentPos =
		axis == 'X' ? Math.round(selectionBounds.left) : Math.round(selectionBounds.top)

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

const performAlignment = (direction) => {
	const axis = ['left', 'centerY', 'right'].includes(direction) ? 'X' : 'Y'
	const value = Math.round(alignmentPositions.value[direction])
	updatePosition(axis, value)
}

const updateGuideVisibilityMap = (direction, value) => {
	guideVisibilityMap[direction] = value
}
</script>
