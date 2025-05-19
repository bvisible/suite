<template>
	<div :style="resizerStyles" @mousedown="$emit('startResize', $event)"></div>
</template>
<script setup>
import { computed } from 'vue'

const props = defineProps({
	resizer: {
		type: String,
		required: true,
	},
})

const emit = defineEmits(['startResize'])

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

const dimensionHandleStyles = {
	width: '7px',
	height: '7px',
}

const getWidthResizerStyles = () => {
	return {
		...baseStyles,
		...widthHandleStyles,
		left: props.resizer === 'resizer-left' ? '-3px' : 'auto',
		right: props.resizer === 'resizer-right' ? '-3px' : 'auto',
	}
}

const getDimensionResizerStyles = () => {
	const resizer = props.resizer
	const cursorStyles = {
		'resizer-top-left': 'nwse-resize',
		'resizer-top-right': 'nesw-resize',
		'resizer-bottom-left': 'nesw-resize',
		'resizer-bottom-right': 'nwse-resize',
	}
	return {
		...baseStyles,
		...dimensionHandleStyles,
		top: resizer.includes('top') ? '-4.5px' : 'auto',
		bottom: resizer.includes('bottom') ? '-4.5px' : 'auto',
		left: resizer.includes('left') ? '-4.5px' : 'auto',
		right: resizer.includes('right') ? '-4.5px' : 'auto',
		cursor: cursorStyles[resizer],
	}
}

const resizerStyles = computed(() => {
	switch (props.resizer) {
		case 'resizer-left':
		case 'resizer-right':
			return getWidthResizerStyles()
		case 'resizer-top-left':
		case 'resizer-top-right':
		case 'resizer-bottom-left':
		case 'resizer-bottom-right':
			return getDimensionResizerStyles()
		default:
			return {}
	}
})
</script>
