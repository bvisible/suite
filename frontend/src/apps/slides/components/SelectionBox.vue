<template>
	<div v-show="selectionBounds.width" ref="selected" :style="boxStyles"></div>
</template>

<script setup>
import { ref, computed, nextTick, useTemplateRef, onMounted, onBeforeUnmount, inject } from 'vue'

import { slide, slideBounds, selectionBounds } from '@/stores/slide'
import {
	activeElementIds,
	setActiveElements,
	getElementPosition,
	resetFocus,
} from '@/stores/element'

const slideDiv = inject('slideDiv')
const slideContainerDiv = inject('slideContainerDiv')

const selectedRef = useTemplateRef('selected')

const startX = ref(0)
const startY = ref(0)

let mousedownTimer = 0
let longpressDuration = 200
let mousedownStart

const boxStyles = computed(() => ({
	position: 'absolute',
	zIndex: 1000,
	backgroundColor: activeElementIds.value.length == 1 ? '' : '#70b6f018',
	border: activeElementIds.value.length == 1 ? '' : '0.1px solid #70b6f092',
	width: `${selectionBounds.width}px`,
	height: `${selectionBounds.height}px`,
	left: `${selectionBounds.left}px`,
	top: `${selectionBounds.top}px`,
	boxSizing: 'border-box',
}))

const initSelection = (e) => {
	activeElementIds.value = []
	nextTick(() => {
		const currentX = (e.clientX - slideBounds.left) / slideBounds.scale
		const currentY = (e.clientY - slideBounds.top) / slideBounds.scale

		selectionBounds.left = currentX
		selectionBounds.top = currentY

		selectionBounds.width = 0
		selectionBounds.height = 0

		startX.value = currentX
		startY.value = currentY
	})

	document.addEventListener('mousemove', updateSelection)
}

const updateSelection = (e) => {
	const currentX = (e.clientX - slideBounds.left) / slideBounds.scale
	const currentY = (e.clientY - slideBounds.top) / slideBounds.scale

	selectionBounds.width = Math.abs(currentX - startX.value)
	selectionBounds.height = Math.abs(currentY - startY.value)

	if (currentX < startX.value) selectionBounds.left = currentX
	if (currentY < startY.value) selectionBounds.top = currentY

	document.addEventListener('mouseup', endSelection)
}

const removeSelectionBox = () => {
	selectionBounds.left = 0
	selectionBounds.top = 0
	selectionBounds.width = 0
	selectionBounds.height = 0
}

const getElementsWithinBoxSurface = () => {
	let elements = []

	const boxLeft = selectionBounds.left
	const boxTop = selectionBounds.top
	const boxRight = selectionBounds.left + selectionBounds.width
	const boxBottom = selectionBounds.top + selectionBounds.height

	slide.value.elements.forEach((element) => {
		const {
			left: elementLeft,
			top: elementTop,
			right: elementRight,
			bottom: elementBottom,
		} = getElementPosition(element.id)

		const withinWidth =
			(boxRight >= elementLeft && boxLeft <= elementLeft) ||
			(elementRight >= boxLeft && elementLeft <= boxLeft)

		const withinHeight =
			(boxBottom >= elementTop && boxTop <= elementTop) ||
			(elementBottom >= boxTop && elementTop <= boxTop)

		if (withinWidth && withinHeight) {
			elements.push(element.id)
		}
	})

	return elements
}

const updateSelectedElements = () => {
	const selectedElements = getElementsWithinBoxSurface()

	if (selectedElements.length) {
		setActiveElements(selectedElements)
	} else {
		removeSelectionBox()
	}
}

const endSelection = (e) => {
	document.removeEventListener('mousemove', updateSelection)

	updateSelectedElements()
}

const cropSelectionToFitContent = (elementIds) => {
	let l = 10000,
		t = 10000,
		r = 0,
		b = 0

	// crop selection to selected element edges
	elementIds.forEach((id) => {
		const {
			left: elementLeft,
			top: elementTop,
			right: elementRight,
			bottom: elementBottom,
		} = getElementPosition(id)

		if (elementLeft < l) l = elementLeft
		if (elementTop < t) t = elementTop
		if (elementRight > r) r = elementRight
		if (elementBottom > b) b = elementBottom
	})

	selectionBounds.left = l
	selectionBounds.top = t
	selectionBounds.width = r - l + 1
	selectionBounds.height = b - t + 1
}

const resetSelection = (oldVal) => {
	selectionBounds.width = 0
	selectionBounds.height = 0
}

const handleMouseDown = (e) => {
	// ignore long press outside slideContainer and slide elements
	if (
		![slideDiv.value, slideContainerDiv.value].includes(e.target) &&
		!e.target.hasAttribute('data-index')
	)
		return

	// ignore long press when userSelect is enabled
	if (e.target.getAttribute('contenteditable') == 'true') return

	mousedownStart = new Date().getTime()
	mousedownTimer = setTimeout(() => {
		initSelection(e)
	}, longpressDuration)

	document.addEventListener('mouseup', handleMouseUp)
}

const handleMouseLeave = () => {
	mousedownStart = 0
	clearTimeout(mousedownTimer)
}

const handleMouseUp = (e) => {
	if (new Date().getTime() < mousedownStart + longpressDuration) {
		selectSlide(e)
		clearTimeout(mousedownTimer)
	} else {
		mousedownStart = 0
	}
}

const moveElement = (elementId, movement) => {
	let element = slide.value.elements.find((el) => el.id === elementId)

	element.left += movement.dx
	element.top += movement.dy
}

const moveElementsToSlide = (elementIds) => {
	elementIds.forEach((elementId) => {
		let elementDiv = document.querySelector(`[data-index="${elementId}"]`)
		slideDiv.value.appendChild(elementDiv)
		moveElement(elementId, {
			dx: selectionBounds.left,
			dy: selectionBounds.top,
		})
	})
}

const moveElementsToBox = (elementIds) => {
	elementIds.forEach((elementId) => {
		const elementDiv = document.querySelector(`[data-index="${elementId}"]`)
		selectedRef.value?.appendChild(elementDiv)
		moveElement(elementId, {
			dx: -selectionBounds.left,
			dy: -selectionBounds.top,
		})
	})
}

const handleSelectionChange = (elementIds, oldIds) => {
	resetSelection(oldIds)
	moveElementsToSlide(oldIds)
	if (elementIds.length) {
		document.removeEventListener('mouseup', endSelection)
		cropSelectionToFitContent(elementIds)
		moveElementsToBox(elementIds)
	}
}

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	resetFocus()
}

onMounted(() => {
	document.addEventListener('mousedown', handleMouseDown)
	document.addEventListener('mouseleave', handleMouseLeave)
})

onBeforeUnmount(() => {
	document.removeEventListener('mousedown', handleMouseDown)
	document.removeEventListener('mouseleave', handleMouseLeave)
	document.removeEventListener('mouseup', handleMouseUp)
	document.removeEventListener('mouseup', endSelection)
})

defineExpose({
	handleSelectionChange,
})
</script>
