<template>
	<div v-for="guide in Object.keys(guideStyles)" :key="guide" :style="guideStyles[guide]"></div>
</template>

<script setup>
import { computed } from 'vue'

import { slideBounds, selectionBounds, guideVisibilityMap } from '@/stores/slide'
import { pairElementId } from '@/stores/element'

const props = defineProps({
	visibilityMap: {
		type: Object,
		default: null,
	},
	isDragging: {
		type: Boolean,
		default: false,
	},
})

const commonStyles = {
	position: 'absolute',
	zIndex: 5,
}

const isVisible = (axis) => {
	const closeToSnap = props.isDragging && props.visibilityMap?.[axis]
	const hoveringOverControl = guideVisibilityMap[axis]
	return closeToSnap || hoveringOverControl
}

const getCenterStyles = (axis) => {
	return {
		...commonStyles,
		backgroundColor: '#70b6f080',
		width: axis === 'centerY' ? '1px' : '100%',
		height: axis === 'centerX' ? '1px' : '100%',
		left: axis === 'centerY' ? '50%' : '0',
		top: axis === 'centerX' ? '50%' : '0',
		display: isVisible(axis) ? 'block' : 'none',
	}
}

const pairedDiv = computed(() => {
	return document.querySelector(`[data-index="${pairElementId.value}"]`)
})

const getScaledValue = (value, axis) => {
	if (axis == 'X') return (value - slideBounds.left) / slideBounds.scale
	return (value - slideBounds.top) / slideBounds.scale
}

const getElementBounds = (div) => {
	const rect = div.getBoundingClientRect()
	return {
		left: getScaledValue(rect.left, 'X'),
		top: getScaledValue(rect.top, 'Y'),
		right: getScaledValue(rect.right, 'X'),
		bottom: getScaledValue(rect.bottom, 'Y'),
		height: rect.height / slideBounds.scale,
		width: rect.width / slideBounds.scale,
	}
}

const getVerticalStyles = (direction) => {
	if (!pairElementId.value || !props.visibilityMap[direction]) return ''

	const pairedBounds = getElementBounds(pairedDiv.value)

	const left =
		direction == 'left'
			? selectionBounds.left - 1
			: selectionBounds.left + selectionBounds.width
	const top = Math.min(selectionBounds.top, pairedBounds.top)
	const lastElementHeight =
		pairedBounds.top < selectionBounds.top ? selectionBounds.height : pairedBounds.height
	const height = Math.abs(pairedBounds.top - selectionBounds.top) + lastElementHeight

	return {
		...commonStyles,
		borderColor: '#70b6f080',
		borderStyle: 'dashed',
		borderWidth: '0 0 0 1px',
		left: `${left}px`,
		top: `${top}px`,
		height: `${height}px`,
		display: isVisible(direction) ? 'block' : 'none',
	}
}

const getHorizontalStyles = (direction) => {
	if (!pairElementId.value || !props.visibilityMap[direction]) return ''

	const pairedBounds = getElementBounds(pairedDiv.value)

	const top =
		direction == 'top' ? selectionBounds.top - 1 : selectionBounds.top + selectionBounds.height
	const left = Math.min(selectionBounds.left, pairedBounds.left)

	const lastElementWidth =
		pairedBounds.left < selectionBounds.left ? selectionBounds.width : pairedBounds.width
	const width = Math.abs(pairedBounds.left - selectionBounds.left) + lastElementWidth

	return {
		...commonStyles,
		borderColor: '#70b6f080',
		borderStyle: 'dashed',
		borderWidth: '1px 0 0 0',
		top: `${top}px`,
		left: `${left}px`,
		width: `${width}px`,
		display: isVisible(direction) ? 'block' : 'none',
	}
}

const getEdgeStyles = (direction) => {
	return {
		...commonStyles,
		width: ['leftEdge', 'rightEdge'].includes(direction) ? '1.5px' : '100%',
		height: ['topEdge', 'bottomEdge'].includes(direction) ? '1.5px' : '100%',
		left: direction == 'rightEdge' ? `calc(100% - 1.5px)` : '0%',
		top: direction == 'bottomEdge' ? `calc(100% - 1.5px)` : '0%',
		display: isVisible(direction) ? 'block' : 'none',
	}
}

const guideStyles = computed(() => {
	return {
		centerX: getCenterStyles('centerX'),
		centerY: getCenterStyles('centerY'),
		left: getVerticalStyles('left'),
		right: getVerticalStyles('right'),
		top: getHorizontalStyles('top'),
		bottom: getHorizontalStyles('bottom'),
		leftEdge: getEdgeStyles('leftEdge'),
		rightEdge: getEdgeStyles('rightEdge'),
		topEdge: getEdgeStyles('topEdge'),
		bottomEdge: getEdgeStyles('bottomEdge'),
	}
})
</script>
