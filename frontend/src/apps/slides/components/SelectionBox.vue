<template>
	<div v-show="width && height" ref="groupDiv" class="groupDiv" :style="boxStyles"></div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useTemplateRef, onMounted, onBeforeUnmount } from 'vue'

import { slide, slideFocus, slideRect } from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElementIds,
	setActiveElements,
	resetFocus,
} from '@/stores/element'

const props = defineProps({
	scale: Number,
})

const emit = defineEmits(['selectSlide'])

const groupDiv = useTemplateRef('groupDiv')

const top = ref(0)
const left = ref(0)
const width = ref(0)
const height = ref(0)
const prevX = ref(0)
const prevY = ref(0)

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
		left.value = (e.clientX - slideRect.value.left) / props.scale
		top.value = (e.clientY - slideRect.value.top) / props.scale
		prevX.value = e.clientX
		prevY.value = e.clientY
		width.value = 0
		height.value = 0
	})

	document.addEventListener('mousemove', updateSelection)
}

const updateSelection = (e) => {
	document.addEventListener('mouseup', endSelection)

	const dx = (e.clientX - prevX.value) / props.scale
	const dy = (e.clientY - prevY.value) / props.scale

	if (dx < 0) {
		left.value = (e.clientX - slideRect.value.left) / props.scale
	}
	if (dy < 0) {
		top.value = (e.clientY - slideRect.value.top) / props.scale
	}

	width.value = Math.abs(dx)
	height.value = Math.abs(dy)
}

const removeSelectionBox = () => {
	left.value = 0
	top.value = 0
	width.value = 0
	height.value = 0
}

const getElementsWithinBoxSurface = () => {
	let elements = []

	slide.value.elements.forEach((element, index) => {
		const boxLeft = left.value
		const boxTop = top.value
		const boxRight = left.value + width.value
		const boxBottom = top.value + height.value

		const elementLeft = element.left
		const elementTop = element.top
		const elementRight = element.left + element.width
		const elementBottom = element.top + element.height

		const withinWidth =
			(boxRight >= elementLeft && boxLeft <= elementLeft) ||
			(elementRight >= boxLeft && elementLeft <= boxLeft)
		const withinHeight =
			(boxBottom >= elementTop && boxTop <= elementTop) ||
			(elementBottom >= boxTop && elementTop <= boxTop)

		if (withinWidth && withinHeight) {
			elements.push(index)
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
	updateSelectedElements()

	document.removeEventListener('mouseup', endSelection)
	document.removeEventListener('mousemove', updateSelection)
}

const cropSelectionToFitContent = () => {
	let l = 10000,
		t = 10000,
		r = 0,
		b = 0

	// crop selection to selected element edges
	activeElementIds.value.forEach((index) => {
		const element = slide.value.elements[index]

		if (element.left < l) l = element.left
		if (element.top < t) t = element.top
		if (element.left + element.width > r) r = element.left + element.width
		if (element.top + element.height > b) b = element.top + element.height
	})

	prevX.value = 0
	prevY.value = 0
	left.value = l
	top.value = t
	width.value = r - l
	height.value = b - t
}

const setElementPositions = () => {
	activePosition.value = {
		left: left.value + slideRect.value.left,
		top: top.value + slideRect.value.top,
	}

	// set positions relative to the selection box
	activeElementIds.value.forEach((index) => {
		let element = slide.value.elements[index]
		element.left = element.left - left.value - 2.1
		element.top = element.top - top.value - 2.1
	})
}

const handleSelection = (val) => {
	// watch for changes in activeElementIds to auto-highlight duplicated group
	cropSelectionToFitContent()

	setElementPositions()

	// move multiple elements to group div after setting position relative to the selection box
	val.forEach((index) => {
		const elementDiv = document.querySelector(`[data-index="${index}"]`)
		groupDiv.value?.appendChild(elementDiv)
	})
}

const resetSelection = (oldVal) => {
	if (oldVal) {
		oldVal.forEach((index) => {
			let elementDiv = document.querySelector(`[data-index="${index}"]`)
			if (!elementDiv) return
			let element = slide.value.elements[index]
			element.left = left.value + element.left + 2.1
			element.top = top.value + element.top + 2.1
			let slideDiv = document.querySelector('.slide')
			slideDiv.appendChild(elementDiv)
		})
	}
	width.value = 0
	height.value = 0
}

const handleMouseDown = (e) => {
	if (e.target.getAttribute('contenteditable')) return
	mousedownStart = new Date().getTime()
	mousedownTimer = setTimeout(() => {
		initSelection(e)
	}, longpressDuration)
}

const handleMouseLeave = () => {
	mousedownStart = 0
	clearTimeout(mousedownTimer)
}

const handleMouseUp = (e) => {
	if (new Date().getTime() < mousedownStart + longpressDuration) {
		if (e.target.classList.contains('slide')) {
			emit('selectSlide', e)
		} else {
			resetFocus()
			slideFocus.value = false
		}
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
		if (val.length >= 1) {
			handleSelection(val)
		}
	},
)

watch(
	() => activePosition.value,
	(newVal, oldVal) => {
		if (newVal) {
			left.value = newVal.left - slideRect.value.left
			top.value = newVal.top - slideRect.value.top
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
	document.addEventListener('mouseup', handleMouseUp)
})

onBeforeUnmount(() => {
	document.removeEventListener('mousedown', initSelection)
	document.removeEventListener('mouseleave', handleMouseLeave)
	document.removeEventListener('mouseup', handleMouseUp)
})

defineExpose({
	resetSelection,
})
</script>
