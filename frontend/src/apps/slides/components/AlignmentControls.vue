<template>
	<CollapsibleSection title="Alignment">
		<template #default>
			<Button label="Backward" @click="sendBackward" />
			<Button label="Back" @click="sendToBack" />
			<Button label="Forward" @click="sendForward" />
			<Button label="Front" @click="sendToFront" />
			<div class="flex items-center gap-3">
				<NumberInput
					:modelValue="selectionBounds.left"
					@update:modelValue="(val) => updatePosition('X', val)"
					prefix="x"
					:rangeStart="0"
					:rangeStep="1"
					:hideButtons="true"
				/>
				<NumberInput
					:modelValue="selectionBounds.top"
					@update:modelValue="(val) => updatePosition('Y', val)"
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

import { slideBounds, selectionBounds, guideVisibilityMap, currentSlide } from '@/stores/slide'
import { fieldLabelClasses } from '@/utils/constants'
import { activeElements, getElementPosition, normalizeZIndices } from '@/stores/element'

import { cloneObj } from '@/utils/helpers'

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

const updatePosition = (axis, value) => {
	const property = axis == 'X' ? 'left' : 'top'

	const delta = value - selectionBounds[property]

	activeElements.value.forEach((element) => {
		element[property] += delta
	})

	selectionBounds[property] = value
}

const moveElement = (elements, elementId, moveToIndex, action) => {
	const movingElement = elements.find((el) => el.id == elementId)

	elements.forEach((el) => {
		if (
			action.includes('back') &&
			el.zIndex >= moveToIndex &&
			el.zIndex < movingElement.zIndex
		) {
			el.zIndex += 1
		} else {
			if (el.zIndex <= moveToIndex && el.zIndex > movingElement.zIndex) {
				el.zIndex -= 1
			}
		}
	})

	movingElement.zIndex = moveToIndex
}

const getElementLists = (action) => {
	// use cloned objects so changes are applied all at once
	// for cleaner history updation
	const elements = cloneObj(currentSlide.value.elements)
	const active = cloneObj(activeElements.value)

	const sortedActiveElements = ['back', 'backward'].includes(action)
		? active.sort((a, b) => a.zIndex - b.zIndex)
		: active.sort((a, b) => b.zIndex - a.zIndex)

	return {
		elements,
		sortedActiveElements,
	}
}

const isElementWithinBounds = (activeId, elementId) => {
	const {
		left: activeLeft,
		top: activeTop,
		right: activeRight,
		bottom: activeBottom,
	} = getElementPosition(activeId)

	const {
		left: elementLeft,
		top: elementTop,
		right: elementRight,
		bottom: elementBottom,
	} = getElementPosition(elementId)

	const withinWidth =
		(activeRight >= elementLeft && activeLeft <= elementLeft) ||
		(elementRight >= activeLeft && elementLeft <= activeLeft)

	const withinHeight =
		(activeBottom >= elementTop && activeTop <= elementTop) ||
		(elementBottom >= activeTop && elementTop <= activeTop)

	return withinWidth && withinHeight
}

const initMoveToIndexAndFactor = (elements, sortedActiveElements, action) => {
	const baseIndex = sortedActiveElements[0].zIndex
	let moveToIndex = null

	const isOverlappingElement = (el) => {
		const isBackward = action == 'backward' && el.zIndex < baseIndex
		const isForward = action == 'forward' && el.zIndex > baseIndex

		if (isBackward || isForward) {
			return isElementWithinBounds(sortedActiveElements[0].id, el.id)
		}
		return false
	}

	switch (action) {
		case 'back':
			return { moveToIndex: 1, factor: 1 }
		case 'front':
			return { moveToIndex: elements.length, factor: -1 }
		case 'backward':
			const lowerZIndices = elements
				.filter((el) => isOverlappingElement(el))
				.map((el) => el.zIndex)
			return {
				moveToIndex: lowerZIndices.length ? Math.max(...lowerZIndices) : 1,
				factor: 1,
			}
		case 'forward':
			const higherZIndices = elements
				.filter((el) => isOverlappingElement(el))
				.map((el) => el.zIndex)
			return {
				moveToIndex: higherZIndices.length ? Math.min(...higherZIndices) : elements.length,
				factor: -1,
			}
		default:
			return { moveToIndex: baseIndex, factor: 1 }
	}
}

const getElementsWithUpdatedZIndices = (action) => {
	const { elements, sortedActiveElements } = getElementLists(action)

	let { moveToIndex, factor } = initMoveToIndexAndFactor(elements, sortedActiveElements, action)

	sortedActiveElements.forEach((element) => {
		moveElement(elements, element.id, moveToIndex, action)

		// next element will move one position above the previous one
		moveToIndex += factor
	})

	return normalizeZIndices(elements)
}

const sendBackward = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('backward')
}

const sendToBack = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('back')
}

const sendForward = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('forward')
}

const sendToFront = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('front')
}
</script>
