<template>
	<div
		:style="resizerStyles"
		@mousedown="$emit('startResize', $event)"
		@dblclick="handleDoubleClick"
	></div>
</template>
<script setup>
import { computed } from 'vue'

import { slideBounds } from '@/stores/slide'

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
	zIndex: 5,
	backgroundColor: '#70b6f0',
	borderRadius: '10px',
}

const getWidthResizerStyles = () => {
	const offsetX = `-${3 / slideBounds.scale}px`
	return {
		...baseStyles,
		cursor: 'ew-resize',
		left: props.direction === 'left' ? offsetX : 'auto',
		right: props.direction === 'right' ? offsetX : 'auto',
		top: `calc(50% - ${7 / slideBounds.scale}px)`,
		width: `${4 / slideBounds.scale}px`,
		height: `${14 / slideBounds.scale}px`,
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
	const offset = props.currentResizer
		? `-${5 / slideBounds.scale}px`
		: `-${4.5 / slideBounds.scale}px`
	const size = props.currentResizer ? `${10 / slideBounds.scale}px` : `${7 / slideBounds.scale}px`
	return {
		...baseStyles,
		top: resizer.includes('top') ? offset : 'auto',
		bottom: resizer.includes('bottom') ? offset : 'auto',
		left: resizer.includes('left') ? offset : 'auto',
		right: resizer.includes('right') ? offset : 'auto',
		width: size,
		height: size,
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
