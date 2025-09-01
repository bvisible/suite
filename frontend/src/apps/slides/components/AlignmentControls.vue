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
import { activeElements, normalizeZIndices } from '@/stores/element'

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

const isElementOverlapping = (activeBounds, element) => {
	let elements = []

	const activeRect = document
		.querySelector(`[data-index="${activeBounds.id}"]`)
		.getBoundingClientRect()

	const activeLeft = activeRect.left - slideBounds.left / slideBounds.scale
	const activeTop = activeRect.top - slideBounds.top / slideBounds.scale
	const activeRight = activeLeft + activeRect.width / slideBounds.scale
	const activeBottom = activeTop + activeRect.height / slideBounds.scale

	const elementRect = document
		.querySelector(`[data-index="${element.id}"]`)
		.getBoundingClientRect()

	const elementLeft = elementRect.left - slideBounds.left / slideBounds.scale
	const elementTop = elementRect.top - slideBounds.top / slideBounds.scale
	const elementRight = elementLeft + elementRect.width / slideBounds.scale
	const elementBottom = elementTop + elementRect.height / slideBounds.scale

	const withinWidth =
		(activeRight >= elementLeft && activeLeft <= elementLeft) ||
		(elementRight >= activeLeft && elementLeft <= activeLeft)

	const withinHeight =
		(activeBottom >= elementTop && activeTop <= elementTop) ||
		(elementBottom >= activeTop && elementTop <= activeTop)

	if (withinWidth && withinHeight) {
		return true
	}

	return false
}

const getElementsWithUpdatedZIndices = (action) => {
	const { elements, sortedActiveElements } = getElementLists(action)

	let moveToIndex = null
	let factor = 1

	if (action == 'back') {
		// start moving elements to bottom
		moveToIndex = 1
	} else if (action == 'backward') {
		// start moving elements to one position below least zIndex
		const leastZIndex = sortedActiveElements[0].zIndex

		const lower = [...elements]
			.filter(
				(el) =>
					el.zIndex < leastZIndex && isElementOverlapping(sortedActiveElements[0], el),
			)
			.map((el) => el.zIndex)

		moveToIndex = lower.length ? Math.max(...lower) : 1
	} else if (action == 'front') {
		// start moving elements to top
		moveToIndex = elements.length
		factor = -1
	} else if (action == 'forward') {
		// start moving elements to one position above highest zIndex
		const highestZIndex = sortedActiveElements[0].zIndex
		const higher = [...elements]
			.filter(
				(el) =>
					el.zIndex > highestZIndex && isElementOverlapping(sortedActiveElements[0], el),
			)
			.map((el) => el.zIndex)

		moveToIndex = higher.length ? Math.min(...higher) : highestZIndex
		factor = -1
	}

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
