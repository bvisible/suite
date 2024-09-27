<template>
	<div class="h-full w-full" ref="resizer">
		<div v-if="element.type == 'text'">
			<div
				v-if="props.resizeWidth"
				ref="rightResizer"
				:class="widthResizerClasses"
				class="-right-[2.5px] top-[calc(50%-6px)]"
			></div>
			<div
				v-if="props.resizeWidth"
				ref="leftResizer"
				:class="widthResizerClasses"
				class="-left-[2.5px] top-[calc(50%-6px)]"
			></div>
			<div
				v-if="props.resizeHeight"
				ref="topResizer"
				:class="heightResizerClasses"
				class="-top-[2.5px] left-[calc(50%-6px)]"
			></div>
			<div
				v-if="props.resizeHeight"
				ref="bottomResizer"
				:class="heightResizerClasses"
				class="-bottom-[2.5px] left-[calc(50%-6px)]"
			></div>
		</div>

		<div v-else="element.type == 'image'">
			<div
				v-if="props.resizeWidth"
				ref="rightResizer"
				:class="widthResizerClasses"
				class="-bottom-[3px] -right-[3px]"
			></div>
			<div
				v-if="props.resizeWidth"
				ref="leftResizer"
				:class="widthResizerClasses"
				class="-left-[3px] -top-[3px]"
			></div>
			<div
				v-if="props.resizeHeight"
				ref="topResizer"
				:class="heightResizerClasses"
				class="-right-[3px] -top-[3px]"
			></div>
			<div
				v-if="props.resizeHeight"
				ref="bottomResizer"
				:class="heightResizerClasses"
				class="-bottom-[3px] -left-[3px]"
			></div>
		</div>
	</div>
</template>

<script setup>
import { ref, unref, onMounted, useTemplateRef, onBeforeUnmount, computed } from 'vue'
import { useElementBounding } from '@vueuse/core'

const resizerRef = useTemplateRef('resizer')

const rect = useElementBounding(resizerRef)

const props = defineProps({
	resizeWidth: {
		type: Boolean,
		default: true,
	},
	resizeHeight: {
		type: Boolean,
		default: true,
	},
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const isResizing = defineModel('isResizing', {
	type: Boolean,
	default: false,
})

const widthResizerClasses = computed(() => {
	if (element.value.type == 'text')
		return ['w-1', 'h-3', 'bg-blue-400', 'rounded-md', 'absolute', 'cursor-ew-resize']
	else return ['w-1.5', 'h-1.5', 'bg-blue-400', 'rounded-md', 'absolute', 'cursor-nwse-resize']
})

const heightResizerClasses = computed(() => {
	if (element.value.type == 'text')
		return ['w-3', 'h-1', 'bg-blue-400', 'rounded-md', 'absolute', 'cursor-ew-resize']
	else return ['w-1.5', 'h-1.5', 'bg-blue-400', 'rounded-md', 'absolute', 'cursor-nesw-resize']
})

let original_x = null
let original_y = null
let original_width = null
let original_height = null
let original_mouse_x = 0
let original_mouse_y = 0

const currentResizer = ref(null)

const topResizerRef = useTemplateRef('topResizer')
const leftResizerRef = useTemplateRef('leftResizer')
const bottomResizerRef = useTemplateRef('bottomResizer')
const rightResizerRef = useTemplateRef('rightResizer')

const startResize = (e) => {
	e.preventDefault()
	e.stopPropagation()
	isResizing.value = true
	currentResizer.value =
		e.target == topResizerRef.value
			? 'top'
			: e.target == rightResizerRef.value
				? 'right'
				: e.target == bottomResizerRef.value
					? 'bottom'
					: 'left'

	original_mouse_x = e.pageX
	original_mouse_y = e.pageY
	original_width = unref(rect.width)
	original_height = unref(rect.height)
	original_x = parseInt(element.value.left)
	original_y = parseInt(element.value.top)

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
		if (e.offsetX == 0) return
		newWidth = original_width - (e.pageX - original_mouse_x)
		if (newWidth > 30) {
			element.value.top = original_y + (e.pageY - original_mouse_y) + 'px'
			element.value.left = original_x + (e.pageX - original_mouse_x) + 'px'
			element.value.width = `${newWidth}px`
		}
	} else if (currentResizer.value == 'right') {
		newWidth = original_width + (e.pageX - original_mouse_x)
		if (newWidth > 30) element.value.width = `${newWidth}px`
	} else if (currentResizer.value == 'top') {
		newHeight = original_height - (e.pageY - original_mouse_y)
		newWidth = (newHeight * original_width) / original_height
		if (newWidth > 30) {
			element.value.top = original_y + (e.pageY - original_mouse_y) + 'px'
			element.value.width = `${newWidth}px`
		}
	} else {
		if (e.offsetX == 0) return
		newHeight = original_height + (e.pageY - original_mouse_y)
		newWidth = (newHeight * original_width) / original_height
		if (newWidth > 30) {
			element.value.left = original_x + (e.pageX - original_mouse_x) + 'px'
			element.value.width = `${newWidth}px`
		}
	}
}

onMounted(() => {
	if (props.resizeWidth) {
		leftResizerRef.value.addEventListener('mousedown', startResize)
		rightResizerRef.value.addEventListener('mousedown', startResize)
	}
	if (props.resizeHeight) {
		topResizerRef.value.addEventListener('mousedown', startResize)
		bottomResizerRef.value.addEventListener('mousedown', startResize)
	}
})

onBeforeUnmount(() => {
	if (props.resizeWidth) {
		leftResizerRef.value.removeEventListener('mousedown', startResize)
		rightResizerRef.value.removeEventListener('mousedown', startResize)
	}
	if (props.resizeHeight) {
		topResizerRef.value.removeEventListener('mousedown', startResize)
		bottomResizerRef.value.removeEventListener('mousedown', startResize)
	}
})
</script>
