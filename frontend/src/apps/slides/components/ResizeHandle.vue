<template>
	<div
		:style="resizerStyles"
		@mousedown="$emit('startResize', $event)"
		@dblclick="handleDoubleClick"
	></div>
</template>
<script setup>
import { computed } from 'vue'

const props = defineProps({
	direction: {
		type: String,
		required: true,
	},
	currentResizer: {
		type: String,
		default: null,
	},
})

const emit = defineEmits(['startResize', 'resizeToFitContent'])

const baseStyles = {
	position: 'absolute',
	zIndex: 100,
	backgroundColor: '#70b6f0',
	borderRadius: '10px',
}

const widthHandleStyles = {
	width: '4px',
	height: '14px',
	cursor: 'ew-resize',
	top: 'calc(50% - 7px)',
}

const getWidthResizerStyles = () => {
	return {
		...baseStyles,
		...widthHandleStyles,
		left: props.direction === 'left' ? '-3px' : 'auto',
		right: props.direction === 'right' ? '-3px' : 'auto',
	}
}

const getDimensionResizerStyles = () => {
	const resizer = props.direction
	const cursorStyles = {
		'top-left': 'nwse-resize',
		'top-right': 'nesw-resize',
		'bottom-left': 'nesw-resize',
		'bottom-right': 'nwse-resize',
	}
	const offset = props.currentResizer ? '-5px' : '-4.5px'
	return {
		...baseStyles,
		top: resizer.includes('top') ? offset : 'auto',
		bottom: resizer.includes('bottom') ? offset : 'auto',
		left: resizer.includes('left') ? offset : 'auto',
		right: resizer.includes('right') ? offset : 'auto',
		width: props.currentResizer ? '10px' : '7px',
		height: props.currentResizer ? '10px' : '7px',
		cursor: cursorStyles[resizer],
	}
}

const resizerStyles = computed(() => {
	switch (props.direction) {
		case 'left':
		case 'right':
			return getWidthResizerStyles()
		case 'top-left':
		case 'top-right':
		case 'bottom-left':
		case 'bottom-right':
			return getDimensionResizerStyles()
		default:
			return {}
	}
})

const handleDoubleClick = (e) => {
	e.stopPropagation()

	if (['left', 'right'].includes(props.direction)) {
		emit('resizeToFitContent', e)
	}
}
</script>
