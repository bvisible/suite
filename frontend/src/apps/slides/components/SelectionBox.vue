<template>
	<div ref="groupDiv" class="groupDiv" :style="boxStyles"></div>
</template>

<script setup>
import { ref, computed, useTemplateRef, onMounted, onBeforeUnmount } from 'vue'

import { slideRect, slide } from '@/stores/slide'
import { activeElementId, activeElementIds, activePosition } from '@/stores/element'

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
	backgroundColor: '#70b6f018',
	border: '1px solid #70b6f092',
	zIndex: 1000,
	width: `${width.value}px`,
	height: `${height.value}px`,
	left: `${left.value}px`,
	top: `${top.value}px`,
}))

const handleMouseDown = (e) => {
	if (e.target != document.querySelector('.slide')) return

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
		clearTimeout(mousedownTimer)
		emit('selectSlide', e)
	} else {
		mousedownStart = 0
	}
}

const updateSelectedElements = () => {
	let selectedElements = []
	slide.value.elements.forEach((element, index) => {
		const withinWidth =
			(left.value + width.value >= element.left && left.value <= element.left) ||
			(element.left + element.width >= left.value && element.left <= left.value)
		const withinHeight =
			(top.value + height.value >= element.top && top.value <= element.top) ||
			(element.top + element.height >= top.value && element.top <= top.value)

		if (withinWidth && withinHeight) {
			selectedElements.push(index)
			const elementDiv = document.querySelector(`[data-index="${index}"]`)
			groupDiv.value.appendChild(elementDiv)
		}
	})
	activeElementIds.value = selectedElements
}

const initSelection = (e) => {
	left.value = e.clientX - slideRect.value.left
	top.value = e.clientY - slideRect.value.top
	prevX.value = e.clientX
	prevY.value = e.clientY
	width.value = 0
	height.value = 0
	activeElementIds.value = []
	activeElementIds.value.forEach((index) => {
		const elementDiv = document.querySelector(`[data-index="${index}"]`)
		groupDiv.value.parentElement.appendChild(elementDiv)
	})
	document.addEventListener('mousemove', updateSelection)
}

const updateSelection = (e) => {
	document.addEventListener('mouseup', endSelection)

	const dx = e.clientX - prevX.value
	const dy = e.clientY - prevY.value

	if (dx < 0) {
		left.value = e.clientX - slideRect.value.left
	}
	if (dy < 0) {
		top.value = e.clientY - slideRect.value.top
	}

	width.value = Math.abs(dx)
	height.value = Math.abs(dy)
}

const clearSelection = () => {
	left.value = 0
	top.value = 0
	width.value = 0
	height.value = 0
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

	// subtract the outlineOffset - (value from SlideElement outlineOffset) for outlines to match up
	prevX.value = 0
	prevY.value = 0
	left.value = l - 7
	top.value = t - 7
	width.value = r - l + 16
	height.value = b - t + 11
}

const setElementPositions = () => {
	activePosition.value = { left: left.value, top: top.value }

	activeElementIds.value.forEach((index) => {
		let element = slide.value.elements[index]
		element.left = element.left - left.value
		element.top = element.top - top.value
	})
}

const endSelection = () => {
	updateSelectedElements()

	// if nothing got selected then clear the selection
	if (activeElementIds.value.length === 0) {
		clearSelection()
	}

	cropSelectionToFitContent()
	setElementPositions()

	document.removeEventListener('mouseup', endSelection)
	document.removeEventListener('mousemove', updateSelection)
}

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
	clearSelection,
})
</script>
