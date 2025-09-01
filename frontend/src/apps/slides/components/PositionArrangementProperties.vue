<template>
	<CollapsibleSection title="Position & Arrange" :initialState="false">
		<template #default>
			<div :class="fieldLabelClasses">Position</div>
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

			<div :class="fieldLabelClasses">Arrange</div>
			<div class="flex items-center gap-3">
				<Button
					variant="outline"
					class="w-1/2 border-gray-200 text-sm text-gray-600 opacity-85"
					label="Backward"
					@click="sendBackward"
				>
					<template #prefix>
						<Backward size="16" :strokeWidth="1.5" />
					</template>
				</Button>

				<Button
					variant="outline"
					class="w-1/2 border-gray-200 text-sm text-gray-600 opacity-85"
					label="Forward"
					@click="sendForward"
				>
					<template #prefix>
						<Forward size="16" :strokeWidth="1.5" />
					</template>
				</Button>
			</div>
			<div class="flex items-center gap-3">
				<Button
					variant="outline"
					class="w-1/2 border-gray-200 text-sm text-gray-600 opacity-85"
					label="To Back"
					@click="sendToBack"
				>
					<template #prefix>
						<SendToBack size="16" :strokeWidth="1.5" />
					</template>
				</Button>

				<Button
					variant="outline"
					class="w-1/2 border-gray-200 text-sm text-gray-600 opacity-85"
					label="To Front"
					@click="bringToFront"
				>
					<template #prefix>
						<BringToFront size="16" :strokeWidth="1.5" />
					</template>
				</Button>
			</div>
		</template>
	</CollapsibleSection>
</template>

<script setup>
import { selectionBounds, currentSlide } from '@/stores/slide'
import {
	activeElements,
	updatePosition,
	getElementPosition,
	isWithinOverlappingBounds,
	normalizeZIndices,
} from '@/stores/element'
import { fieldLabelClasses } from '@/utils/constants'
import { cloneObj } from '@/utils/helpers'

import Forward from '@/icons/Forward.vue'
import Backward from '@/icons/Backward.vue'
import SendToBack from '@/icons/SendToBack.vue'
import BringToFront from '@/icons/BringToFront.vue'
import CollapsibleSection from './controls/CollapsibleSection.vue'

const moveElement = (elements, elementId, moveToIndex, action) => {
	const movingElement = elements.find((el) => el.id == elementId)
	const currentZIndex = movingElement.zIndex

	elements.forEach((el) => {
		const zIndex = el.zIndex
		if (action.includes('back') && zIndex >= moveToIndex && zIndex < currentZIndex) {
			el.zIndex += 1
		} else if (action.includes('front') && zIndex <= moveToIndex && zIndex > currentZIndex) {
			el.zIndex -= 1
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
	const activePosition = getElementPosition(activeId)
	const elementPosition = getElementPosition(elementId)

	return isWithinOverlappingBounds(activePosition, elementPosition)
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

const bringToFront = () => {
	currentSlide.value.elements = getElementsWithUpdatedZIndices('front')
}
</script>
