<template>
	<div v-show="bounds.width" ref="selected" :style="boxStyles"></div>
</template>

<script setup>
import {
	ref,
	computed,
	watch,
	nextTick,
	useTemplateRef,
	onMounted,
	onBeforeUnmount,
	reactive,
} from 'vue'

import { slide, slideDimensions } from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElementIds,
	setActiveElements,
	moveElement,
} from '@/stores/element'

const emit = defineEmits(['updateFocus'])

const selectedRef = useTemplateRef('selected')

const bounds = reactive({
	left: 0,
	top: 0,
	width: 0,
	height: 0,
})

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
	width: `${bounds.width}px`,
	height: `${bounds.height}px`,
	left: `${bounds.left}px`,
	top: `${bounds.top}px`,
	boxSizing: 'border-box',
}))

const initSelection = (e) => {
	activeElementIds.value = []
	nextTick(() => {
		const currentX = (e.clientX - slideDimensions.left) / slideDimensions.scale
		const currentY = (e.clientY - slideDimensions.top) / slideDimensions.scale

		bounds.left = currentX
		bounds.top = currentY

		bounds.width = 0
		bounds.height = 0

		startX.value = currentX
		startY.value = currentY
	})

	document.addEventListener('mousemove', updateSelection)
}

const updateSelection = (e) => {
	const currentX = (e.clientX - slideDimensions.left) / slideDimensions.scale
	const currentY = (e.clientY - slideDimensions.top) / slideDimensions.scale

	bounds.width = Math.abs(currentX - startX.value)
	bounds.height = Math.abs(currentY - startY.value)

	if (currentX < startX.value) bounds.left = currentX
	if (currentY < startY.value) bounds.top = currentY

	document.addEventListener('mouseup', endSelection)
}

const removeSelectionBox = () => {
	bounds.left = 0
	bounds.top = 0
	bounds.width = 0
	bounds.height = 0
}

const getElementsWithinBoxSurface = () => {
	let elements = []

	const boxLeft = bounds.left
	const boxTop = bounds.top
	const boxRight = bounds.left + bounds.width
	const boxBottom = bounds.top + bounds.height

	slide.value.elements.forEach((element) => {
		const elementRect = document
			.querySelector(`[data-index="${element.id}"]`)
			.getBoundingClientRect()

		const elementLeft = (elementRect.left - slideDimensions.left) / slideDimensions.scale
		const elementTop = (elementRect.top - slideDimensions.top) / slideDimensions.scale
		const elementRight = elementLeft + elementRect.width / slideDimensions.scale
		const elementBottom = elementTop + elementRect.height / slideDimensions.scale

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
		const elementRect = document.querySelector(`[data-index="${id}"]`).getBoundingClientRect()

		const elementLeft = (elementRect.left - slideDimensions.left) / slideDimensions.scale
		const elementTop = (elementRect.top - slideDimensions.top) / slideDimensions.scale
		const elementRight = elementLeft + elementRect.width / slideDimensions.scale
		const elementBottom = elementTop + elementRect.height / slideDimensions.scale

		if (elementLeft < l) l = elementLeft
		if (elementTop < t) t = elementTop
		if (elementRight > r) r = elementRight
		if (elementBottom > b) b = elementBottom
	})

	bounds.left = l
	bounds.top = t
	bounds.width = r - l
	bounds.height = b - t
}

const resetSelection = (oldVal) => {
	bounds.width = 0
	bounds.height = 0
}

const handleMouseDown = (e) => {
	// ignore long press outside slideContainer and slide elements
	if (
		!['slide', 'slideContainer'].some((cls) => e.target.classList.contains(cls)) &&
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
		emit('updateFocus', e)
		clearTimeout(mousedownTimer)
	} else {
		mousedownStart = 0
	}
}

const moveElementsToSlide = (elementIds) => {
	elementIds.forEach((elementId) => {
		let elementDiv = document.querySelector(`[data-index="${elementId}"]`)
		let slideDiv = document.querySelector('.slide')
		slideDiv.appendChild(elementDiv)
		moveElement(elementId, {
			dx: bounds.left,
			dy: bounds.top,
		})
	})
}

const moveElementsToBox = (elementIds) => {
	elementIds.forEach((elementId) => {
		const elementDiv = document.querySelector(`[data-index="${elementId}"]`)
		selectedRef.value?.appendChild(elementDiv)
		moveElement(elementId, {
			dx: -bounds.left,
			dy: -bounds.top,
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

const getBoxBounds = () => bounds

const setBoxBounds = (newBounds) => {
	Object.keys(newBounds).forEach((key) => {
		bounds[key] = newBounds[key]
	})
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
	getBoxBounds,
	setBoxBounds,
})
</script>
