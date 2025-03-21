<template>
	<div v-show="width" ref="selected" :style="boxStyles"></div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useTemplateRef, onMounted, onBeforeUnmount } from 'vue'

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

const top = ref(0)
const left = ref(0)
const width = ref(0)
const height = ref(0)

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
	width: `${width.value}px`,
	height: `${height.value}px`,
	left: `${left.value}px`,
	top: `${top.value}px`,
	boxSizing: 'border-box',
}))

const initSelection = (e) => {
	activeElementIds.value = []
	nextTick(() => {
		const currentX = (e.clientX - slideDimensions.left) / slideDimensions.scale
		const currentY = (e.clientY - slideDimensions.top) / slideDimensions.scale

		left.value = currentX
		top.value = currentY

		width.value = 0
		height.value = 0

		startX.value = currentX
		startY.value = currentY
	})

	document.addEventListener('mousemove', updateSelection)
}

const updateSelection = (e) => {
	const currentX = (e.clientX - slideDimensions.left) / slideDimensions.scale
	const currentY = (e.clientY - slideDimensions.top) / slideDimensions.scale

	width.value = Math.abs(currentX - startX.value)
	height.value = Math.abs(currentY - startY.value)

	if (currentX < startX.value) left.value = currentX
	if (currentY < startY.value) top.value = currentY

	document.addEventListener('mouseup', endSelection)
}

const removeSelectionBox = () => {
	left.value = 0
	top.value = 0
	width.value = 0
	height.value = 0
}

const getElementsWithinBoxSurface = () => {
	let elements = []

	const boxLeft = left.value
	const boxTop = top.value
	const boxRight = left.value + width.value
	const boxBottom = top.value + height.value

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

const endSelection = () => {
	document.removeEventListener('mousemove', updateSelection)

	updateSelectedElements()
}

const cropSelectionToFitContent = () => {
	let l = 10000,
		t = 10000,
		r = 0,
		b = 0

	// crop selection to selected element edges
	activeElementIds.value.forEach((id) => {
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

	left.value = l
	top.value = t
	width.value = r - l
	height.value = b - t
}

const setElementPositions = () => {
	activePosition.value = {
		left: left.value + slideDimensions.left,
		top: top.value + slideDimensions.top,
	}

	// set positions relative to the selection box
	activeElementIds.value.forEach((id) => {
		slide.value.elements.forEach((element) => {
			if (element.id != id) return
			moveElement(id, {
				dx: -left.value,
				dy: -top.value,
			})
		})
	})
}

const handleSelection = (val) => {
	// watch for changes in activeElementIds to auto-highlight duplicated group
	cropSelectionToFitContent()

	setElementPositions()

	// move multiple elements to group div after setting position relative to the selection box
	val.forEach((index) => {
		const elementDiv = document.querySelector(`[data-index="${index}"]`)
		selectedRef.value?.appendChild(elementDiv)
	})
}

const resetSelection = (oldVal) => {
	if (oldVal) {
		oldVal.forEach((index) => {
			let elementDiv = document.querySelector(`[data-index="${index}"]`)
			if (!elementDiv) return

			moveElement(index, {
				dx: left.value,
				dy: top.value,
			})

			let slideDiv = document.querySelector('.slide')
			slideDiv.appendChild(elementDiv)
		})
	}
	width.value = 0
	height.value = 0
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

watch(
	() => activeElementIds.value,
	(val, oldVal) => {
		if (oldVal.length) {
			resetSelection(oldVal)
		}
		if (val.length) {
			document.removeEventListener('mouseup', endSelection)
			handleSelection(val)
		}
	},
)

watch(
	() => activePosition.value,
	(newVal, oldVal) => {
		if (newVal) {
			left.value = newVal.left - slideDimensions.left
			top.value = newVal.top - slideDimensions.top
		}
	},
	{ immediate: true },
)

watch(
	() => activeDimensions.value,
	(newVal) => {
		if (newVal) {
			width.value = newVal.width
		}
	},
	{ immediate: true },
)

onMounted(() => {
	document.addEventListener('mousedown', handleMouseDown)
	document.addEventListener('mouseleave', handleMouseLeave)
})

onBeforeUnmount(() => {
	document.removeEventListener('mousedown', handleMouseDown)
	document.removeEventListener('mouseleave', handleMouseLeave)
	document.removeEventListener('mouseup', handleMouseUp)
})
</script>
