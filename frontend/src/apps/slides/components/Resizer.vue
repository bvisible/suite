<template>
	<div>
		<ResizeHandle
			v-for="resizeHandle in resizeHandles"
			v-show="resizeHandle.isVisible"
			:key="resizeHandle.direction"
			:direction="resizeHandle.direction"
			@startResize="(e) => startResize(e, resizeHandle.direction)"
			@resizeToFitContent="$emit('resizeToFitContent')"
		/>

		<ResizeIndicator
			v-show="currentResizer"
			:type="elementType"
			:dimensions="dimensions"
			:indicatorStyles="indicatorStyles"
		/>
	</div>
</template>

<script setup>
import { computed, inject, watch } from 'vue'

import ResizeHandle from '@/components/ResizeHandle.vue'
import ResizeIndicator from '@/components/ResizeIndicator.vue'

import { selectionBounds, slideBounds } from '@/stores/slide'

const props = defineProps({
	elementType: {
		type: String,
		required: true,
	},
	dimensions: {
		type: Object,
		default: {},
	},
})

const { currentResizer, startResize } = inject('resizer', {})

const isResizeHandleVisible = (resizer) => {
	if (!currentResizer.value) return true
	return currentResizer.value === resizer
}

const resizeHandles = computed(() => {
	const directions =
		props.elementType === 'text'
			? ['left', 'right']
			: ['top-left', 'top-right', 'bottom-left', 'bottom-right']

	return directions.map((direction) => ({
		direction,
		isVisible: isResizeHandleVisible(direction),
	}))
})

const getScaledValue = (value) => `${value / slideBounds.scale}px`

const getTextIndicatorPosition = () => {
	const resizer = currentResizer.value
	const offsetX = getScaledValue(selectionBounds.width + 20)
	const offsetY = getScaledValue(12)

	return {
		left: resizer.includes('right') ? offsetX : 'auto',
		right: resizer.includes('left') ? offsetX : 'auto',
		top: `calc(50% - ${offsetY})`,
	}
}

const getMediaIndicatorPosition = () => {
	const resizer = currentResizer.value
	const offset = getScaledValue(8)

	return {
		left: resizer.includes('left') ? offset : 'auto',
		right: resizer.includes('right') ? offset : 'auto',
		top: resizer.includes('top') ? offset : 'auto',
		bottom: resizer.includes('bottom') ? offset : 'auto',
	}
}

const getPositionStyles = () => {
	if (props.elementType === 'text') {
		return getTextIndicatorPosition()
	}
	return getMediaIndicatorPosition()
}

const indicatorStyles = computed(() => {
	if (!currentResizer.value) return {}

	const positionStyles = getPositionStyles()

	return {
		fontSize: getScaledValue(10),
		borderRadius: getScaledValue(6),
		padding: getScaledValue(4),
		...positionStyles,
	}
})
</script>
