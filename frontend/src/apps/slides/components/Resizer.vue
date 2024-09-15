<template>
	<div
		ref="rightResizer"
		:class="resizerClasses"
		class="-right-[2.5px] top-[calc(50%-6px)]"
	></div>
	<div ref="leftResizer" :class="resizerClasses" class="-left-[2.5px] top-[calc(50%-6px)]"></div>
</template>

<script setup>
import { ref, unref, onMounted, useTemplateRef, onBeforeUnmount, computed } from 'vue'

const resizerClasses = ['w-1', 'h-3', 'bg-gray-900', 'rounded-md', 'cursor-ew-resize', 'absolute']

const element = defineModel('element', {
	type: Object,
	default: null,
})

const isResizing = defineModel('isResizing', {
	type: Boolean,
	default: false,
})

let original_x = null
let original_width = null
let original_mouse_x = 0

const currentResizer = ref(null)

const leftResizerRef = useTemplateRef('leftResizer')
const rightResizerRef = useTemplateRef('rightResizer')

const startResize = (e) => {
	e.preventDefault()
	e.stopPropagation()
	isResizing.value = true
	currentResizer.value = e.target == rightResizerRef.value ? 'right' : 'left'

	original_mouse_x = e.pageX
	original_width = parseInt(element.value.width)
	original_x = parseInt(element.value.left)

	window.addEventListener('mousemove', resize)
	window.addEventListener('mouseup', stopResize, { once: true })
}

const stopResize = (e) => {
	e.preventDefault()
	e.stopPropagation()
	isResizing.value = false
	window.removeEventListener('mousemove', resize)
}

const resize = (e) => {
	e.preventDefault()
	e.stopPropagation()
	let newWidth = 0
	let newHeight = 0

	if (currentResizer.value == 'left') {
		newWidth = original_width - (e.pageX - original_mouse_x)
		if (newWidth > 30) {
			element.value.left = original_x + (e.pageX - original_mouse_x) + 'px'
			element.value.width = `${newWidth}px`
		}
	} else if (currentResizer.value == 'right') {
		newWidth = original_width + (e.pageX - original_mouse_x)
		if (newWidth > 30) element.value.width = `${newWidth}px`
	}
}

onMounted(() => {
	leftResizerRef.value.addEventListener('mousedown', startResize)
	rightResizerRef.value.addEventListener('mousedown', startResize)
})

onBeforeUnmount(() => {
	leftResizerRef.value.removeEventListener('mousedown', startResize)
	rightResizerRef.value.removeEventListener('mousedown', startResize)
})
</script>
