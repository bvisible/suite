<template>
	<div
		v-for="guide in ['centerX', 'centerY', 'left', 'right', 'top', 'bottom']"
		:key="guide"
		:style="guideStyles[guide]"
	></div>
</template>

<script setup>
import { computed } from 'vue'

import { slideBounds, selectionBounds } from '@/stores/slide'
import { pairElementId } from '@/stores/element'

const props = defineProps({
	visibilityMap: {
		type: Object,
		default: null,
	},
})

const commonStyles = {
	backgroundColor: '#70b6f080',
	position: 'fixed',
}

const getCenterStyles = (axis) => {
	return {
		...commonStyles,
		width: axis === 'horizontal' ? '1px' : '100%',
		height: axis === 'vertical' ? '1px' : '100%',
		left: axis === 'horizontal' ? '50%' : '0',
		top: axis === 'vertical' ? '50%' : '0',
		display: props.visibilityMap?.[axis] ? 'block' : 'none',
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

	const activeBounds = selectionBounds
	const pairedBounds = getElementBounds(pairedDiv.value)

	const left =
		direction == 'left'
			? activeBounds.left - 1
			: activeBounds.left + activeBounds.width * slideBounds.scale
	const top = Math.min(activeBounds.top, pairedBounds.top)
	const lastElementHeight =
		pairedBounds.top < activeBounds.top ? activeBounds.height : pairedBounds.height
	const height = Math.abs(pairedBounds.top - activeBounds.top) + lastElementHeight

	return {
		position: 'fixed',
		borderColor: '#70b6f080',
		borderStyle: 'dashed',
		borderWidth: '0 0 0 1px',
		left: `${left}px`,
		top: `${top}px`,
		height: `${height}px`,
	}
}

const getHorizontalStyles = (direction) => {
	if (!pairElementId.value || !props.visibilityMap[direction]) return ''

	const activeBounds = selectionBounds
	const pairedBounds = getElementBounds(pairedDiv.value)

	const top =
		direction == 'top'
			? activeBounds.top - 1
			: activeBounds.top + activeBounds.height * slideBounds.scale
	const left = Math.min(activeBounds.left, pairedBounds.left)

	const lastElementWidth =
		pairedBounds.left < activeBounds.left ? activeBounds.width : pairedBounds.width
	const width = Math.abs(pairedBounds.left - activeBounds.left) + lastElementWidth

	return {
		position: 'fixed',
		borderColor: '#70b6f080',
		borderStyle: 'dashed',
		borderWidth: '1px 0 0 0',
		top: `${top}px`,
		left: `${left}px`,
		width: `${width}px`,
	}
}

const guideStyles = computed(() => {
	return {
		centerX: getCenterStyles('horizontal'),
		centerY: getCenterStyles('vertical'),
		left: getVerticalStyles('left'),
		right: getVerticalStyles('right'),
		top: getHorizontalStyles('top'),
		bottom: getHorizontalStyles('bottom'),
	}
})
</script>
