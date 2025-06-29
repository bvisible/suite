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

			<div :class="fieldLabelClasses">Horizontal</div>
			<div class="grid grid-cols-3 gap-3">
				<div :class="getAlignmentButtonClasses('left')" @click="performAlignment('left')">
					<AlignStartVertical size="18" :strokeWidth="1.5" />
				</div>
				<div
					:class="getAlignmentButtonClasses('centerX')"
					@click="performAlignment('centerX')"
				>
					<AlignCenterVertical size="18" :strokeWidth="1.5" />
				</div>
				<div :class="getAlignmentButtonClasses('right')" @click="performAlignment('right')">
					<AlignEndVertical size="18" :strokeWidth="1.5" />
				</div>
			</div>

			<div :class="fieldLabelClasses">Vertical</div>
			<div class="grid grid-cols-3 gap-3">
				<div :class="getAlignmentButtonClasses('top')" @click="performAlignment('top')">
					<AlignStartHorizontal size="18" :strokeWidth="1.5" />
				</div>
				<div
					:class="getAlignmentButtonClasses('centerY')"
					@click="performAlignment('centerY')"
				>
					<AlignCenterHorizontal size="18" :strokeWidth="1.5" />
				</div>
				<div
					:class="getAlignmentButtonClasses('bottom')"
					@click="performAlignment('bottom')"
				>
					<AlignEndHorizontal size="18" :strokeWidth="1.5" />
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

import { slideBounds, selectionBounds } from '@/stores/slide'
import { fieldLabelClasses } from '@/utils/constants'

const alignmentPositions = computed(() => {
	const slideWidth = slideBounds.width / slideBounds.scale
	const slideHeight = slideBounds.height / slideBounds.scale

	const { width: selectionWidth, height: selectionHeight } = selectionBounds

	return {
		left: 0,
		centerX: Math.round(slideWidth / 2) - Math.round(selectionWidth / 2),
		right: Math.round(slideWidth) - Math.round(selectionWidth),
		top: 0,
		centerY: Math.round(slideHeight / 2) - Math.round(selectionHeight / 2),
		bottom: Math.round(slideHeight) - Math.round(selectionHeight),
	}
})

const isAligned = (direction) => {
	const axis = ['left', 'centerX', 'right'].includes(direction) ? 'X' : 'Y'

	const expectedPos = alignmentPositions.value[direction]

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

const alignHorizontally = (direction) => {
	selectionBounds.left = Math.round(alignmentPositions.value[direction])
}

const alignVertically = (direction) => {
	selectionBounds.top = Math.round(alignmentPositions.value[direction])
}

const performAlignment = (direction) => {
	switch (direction) {
		case 'left':
		case 'centerX':
		case 'right':
			alignHorizontally(direction)
			break
		default:
			// 'top', 'centerY', 'bottom'
			alignVertically(direction)
			break
	}
}
</script>
