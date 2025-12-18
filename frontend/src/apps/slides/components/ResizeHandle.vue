<template>
	<div :style="resizerStyles" @mousedown="$emit('startResize', $event)"></div>
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

const emit = defineEmits(['startResize'])

const baseStyles = {
	position: 'absolute',
	zIndex: 9999,
	backgroundColor: '#70b6f0',
	borderRadius: '10px',
}

const getWidthResizerStyles = () => {
	const resizer = props.direction

	const offsetX = `-${3 / slideBounds.scale}px`
	return {
		...baseStyles,
		cursor: 'ew-resize',
		left: resizer.includes('left') ? offsetX : 'auto',
		right: resizer.includes('right') ? offsetX : 'auto',
		top: `calc(50% - ${7 / slideBounds.scale}px)`,
		width: `${4 / slideBounds.scale}px`,
		height: `${14 / slideBounds.scale}px`,
	}
}

const getHeightResizerStyles = () => {
	const resizer = props.direction

	const offsetX = `-${3 / slideBounds.scale}px`
	return {
		...baseStyles,
		cursor: 'ns-resize',
		left: `calc(50% - ${7 / slideBounds.scale}px)`,
		top: resizer.includes('top') ? offsetX : 'auto',
		bottom: resizer.includes('bottom') ? offsetX : 'auto',
		width: `${14 / slideBounds.scale}px`,
		height: `${4 / slideBounds.scale}px`,
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
		case 'text-left':
		case 'text-right':
		case 'left':
		case 'right':
			return getWidthResizerStyles()
		case 'top':
		case 'bottom':
			return getHeightResizerStyles()
		case 'top-left':
		case 'top-right':
		case 'bottom-left':
		case 'bottom-right':
			return getDimensionResizerStyles()
		default:
			return {}
	}
})
</script>
