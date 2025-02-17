<template>
	<div v-show="width && height" ref="groupDiv" class="groupDiv" :style="boxStyles"></div>
</template>

<script setup>
import { ref, computed, useTemplateRef, onMounted, onBeforeUnmount, watch } from 'vue'

import { slideRect, slide } from '@/stores/slide'
import {
	activeDimensions,
	activeElementIds,
	activePosition,
	setActiveElements,
} from '@/stores/element'

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
	backgroundColor: activeElementIds.value.length == 1 ? '' : '#70b6f018',
	border: activeElementIds.value.length == 1 ? '' : '0.1px solid #70b6f092',
	zIndex: 1000,
	width: `${width.value}px`,
	height: `${height.value}px`,
	left: `${left.value}px`,
	top: `${top.value}px`,
	boxSizing: 'border-box',
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
		}
	})
	setActiveElements(selectedElements)
}

const initSelection = (e) => {
	left.value = e.clientX - slideRect.value.left
	top.value = e.clientY - slideRect.value.top
	prevX.value = e.clientX
	prevY.value = e.clientY
	width.value = 0
	height.value = 0
	activeElementIds.value = []

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

const resetSelection = (oldVal) => {
	if (oldVal) {
		oldVal.forEach((index) => {
			let elementDiv = document.querySelector(`[data-index="${index}"]`)
			if (!elementDiv) return
			let slideDiv = document.querySelector('.slide')
			slideDiv.appendChild(elementDiv)
			let element = slide.value.elements[index]
			element.left = left.value + element.left + 2.5
			element.top = top.value + element.top + 2.5
		})
	}
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

	prevX.value = 0
	prevY.value = 0
	left.value = l - 2.1
	top.value = t - 2.1
	width.value = r - l - 0.1
	height.value = b - t - 0.1
}

const setElementPositions = () => {
	activePosition.value = { left: left.value, top: top.value }

	// set positions relative to the selection box
	activeElementIds.value.forEach((index) => {
		let element = slide.value.elements[index]
		element.left = element.left - left.value - 2.5
		element.top = element.top - top.value - 2.5
	})
}

const endSelection = () => {
	updateSelectedElements()

	document.removeEventListener('mouseup', endSelection)
	document.removeEventListener('mousemove', updateSelection)
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

watch(
	() => activeElementIds.value,
	(val, oldVal) => {
		if (val.length >= 1) {
			handleSelection(val)
		} else {
			resetSelection(oldVal)
		}
	},
)

watch(
	() => activePosition.value,
	(newVal, oldVal) => {
		if (newVal) {
			left.value = newVal.left
			top.value = newVal.top
		}
	},
	{ immediate: true },
)

watch(
	() => activeDimensions.value,
	(newVal) => {
		if (newVal) {
			width.value = newVal.width - 4
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
