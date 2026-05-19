<template>
	<div v-show="selectionBounds.width" ref="selected" :style="boxStyles">
		<Resizer
			v-if="showResizers"
			:elementType="activeElement?.shapeType || activeElement?.type"
			:dimensions="selectionBounds"
			:style="{ pointerEvents: 'auto' }"
		/>
	</div>
</template>
<script setup>
import { ref, computed, nextTick, useTemplateRef, onMounted, onBeforeUnmount, inject } from 'vue'

import Resizer from '@/components/Resizer.vue'

import { currentSlide, slideBounds, selectionBounds, updateSelectionBounds } from '@/stores/slide'
import {
	activeElementIds,
	setActiveElements,
	getElementPosition,
	resetFocus,
	focusElementId,
	activeElement,
	isWithinOverlappingBounds,
	cropSelectionToFitContent,
} from '@/stores/element'

const slideDiv = inject('slideDiv')
const slideContainerDiv = inject('slideContainerDiv')

const props = defineProps({
	isDragging: {
		type: Boolean,
		default: false,
	},
	rotationDelta: {
		type: Number,
		default: 0,
	},
})

const emit = defineEmits(['setIsSelecting'])

const selectedRef = useTemplateRef('selected')

const showResizers = computed(() => {
	return activeElementIds.value.length == 1 && !focusElementId.value && !props.isDragging
})

const startX = ref(0)
const startY = ref(0)

let mousedownTimer = 0
let longpressDuration = 200
let mousedownStart

const outline = computed(() => {
	if (activeElement.value?.shapeType == 'line') return 'none'

	if (activeElementIds.value.length == 1) return `#70B6F0 solid ${2 / slideBounds.scale}px`
	return `#70B6F092 solid ${0.1 / slideBounds.scale}px`
})

const isRotatable = computed(() => {
	return ['shape', 'image'].includes(activeElement.value?.type)
})

const selectionRotation = computed(() => {
	if (activeElementIds.value.length != 1 || !isRotatable.value) return 0
	return (activeElement.value.rotation || 0) + props.rotationDelta
})

const boxStyles = computed(() => ({
	position: 'absolute',
	backgroundColor: activeElementIds.value.length == 1 ? '' : '#70b6f025',
	outline: outline.value,
	width: `${selectionBounds.width}px`,
	height: `${selectionBounds.height}px`,
	left: `${selectionBounds.left}px`,
	top: `${selectionBounds.top}px`,
	boxSizing: 'border-box',
	zIndex: 9999,
	pointerEvents: activeElementIds.value.length == 1 ? 'none' : 'auto',
	transform: selectionRotation.value ? `rotate(${selectionRotation.value}deg)` : '',
	transformOrigin: 'center center',
}))

const initSelection = (e) => {
	activeElementIds.value = []
	emit('setIsSelecting', true)
	nextTick(() => {
		const currentX = (e.clientX - slideBounds.left) / slideBounds.scale
		const currentY = (e.clientY - slideBounds.top) / slideBounds.scale

		updateSelectionBounds({
			left: currentX,
			top: currentY,
			width: 0,
			height: 0,
		})

		startX.value = currentX
		startY.value = currentY
	})

	document.addEventListener('mousemove', updateSelection)
}

const updateSelection = (e) => {
	const currentX = (e.clientX - slideBounds.left) / slideBounds.scale
	const currentY = (e.clientY - slideBounds.top) / slideBounds.scale

	const newBounds = {
		width: Math.abs(currentX - startX.value),
		height: Math.abs(currentY - startY.value),
	}

	if (currentX < startX.value) {
		newBounds.left = currentX
	}
	if (currentY < startY.value) {
		newBounds.top = currentY
	}

	updateSelectionBounds(newBounds)

	document.addEventListener('mouseup', endSelection)
}

const removeSelectionBox = () => {
	updateSelectionBounds({
		left: 0,
		top: 0,
		width: 0,
		height: 0,
	})
}

const getElementsWithinBoxSurface = () => {
	let elements = []

	const boxBounds = {
		left: selectionBounds.left,
		top: selectionBounds.top,
		right: selectionBounds.left + selectionBounds.width,
		bottom: selectionBounds.top + selectionBounds.height,
	}

	currentSlide.value.elements.forEach((element) => {
		const elementPosition = getElementPosition(element.id)

		const isWithinBounds = isWithinOverlappingBounds(boxBounds, elementPosition)

		if (isWithinBounds) elements.push(element.id)
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
	emit('setIsSelecting', false)

	document.removeEventListener('mousemove', updateSelection)

	updateSelectedElements()
}

const resetSelection = (oldVal) => {
	updateSelectionBounds({
		width: 0,
		height: 0,
		left: 0,
		top: 0,
	})
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

const handleSelection = (elementIds) => {
	if (!elementIds.length) return
	document.removeEventListener('mouseup', endSelection)
	cropSelectionToFitContent(elementIds)
}

const handleSelectionChange = (elementIds, oldIds) => {
	resetSelection(oldIds)
	handleSelection(elementIds)
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
