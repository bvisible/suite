<template>
	<div :style="boxStyles"></div>
</template>

<script setup>
import { slideRect } from '@/stores/slide'
import { onMounted, ref, computed, onBeforeUnmount } from 'vue'
import { slide } from '@/stores/slide'
import { activeElementIds } from '@/stores/element'

const emit = defineEmits(['selectSlide'])

const top = ref(0)
const left = ref(0)
const width = ref(0)
const height = ref(0)

let mousedownTimer = 0
let longpressDuration = 200
let mousedownStart

const boxStyles = computed(() => ({
	position: 'fixed',
	border: '1px solid #70b6f092',
	pointerEvents: 'none',
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
	}
}

const updateSelectedElements = () => {
	activeElementIds.value = []
	slide.value.elements.forEach((element, index) => {
		const withinWidth = left.value <= element.left && left.value + width.value >= element.left
		const withinHeight = top.value <= element.top && top.value + height.value >= element.top
		if (withinWidth && withinHeight) {
			activeElementIds.value.push(index)
		}
	})
}

const initSelection = (e) => {
	document.addEventListener('mousemove', updateSelection)
	left.value = e.clientX - slideRect.value.left
	top.value = e.clientY - slideRect.value.top
	width.value = 0
	height.value = 0
}

const updateSelection = (e) => {
	document.addEventListener('mouseup', endSelection)

	width.value = e.clientX - slideRect.value.left - left.value
	height.value = e.clientY - slideRect.value.top - top.value

	updateSelectedElements()
}

const endSelection = () => {
	document.removeEventListener('mousemove', updateSelection)
	document.removeEventListener('mouseup', endSelection)
}

onMounted(() => {
	document.addEventListener('mousedown', handleMouseDown)
	document.addEventListener('mouseleave', handleMouseLeave)
	document.addEventListener('mouseup', handleMouseUp)
})

onBeforeUnmount(() => {
	document.removeEventListener('mousedown', initSelection)
})
</script>
