<template>
	<div
		:style="indicatorStyles"
		class="backdrop-blur-sm opacity-85 text-black"
		:class="indicatorClasses"
	>
		<i v-if="type === 'text'"> {{ Math.round(selectionBounds.width) }}px </i>
		<template v-else>
			<i>{{ Math.round(selectionBounds.width) }}px</i> ×
			<i>{{ Math.round(selectionBounds.height) }}px</i>
		</template>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { slide, slideBounds, selectionBounds } from '@/stores/slide'
import { isBackgroundColorDark } from '@/utils/color'

const props = defineProps({
	currentResizer: {
		type: String,
		default: null,
	},
	type: {
		type: String,
		default: null,
	},
})

const getScaledOffset = (offset) => `${offset / slideBounds.scale}px`

const getTextIndicatorPosition = () => {
	const resizer = props.currentResizer
	const offsetX = getScaledOffset(selectionBounds.width + 20)
	const offsetY = getScaledOffset(12)

	return {
		left: resizer.includes('right') ? offsetX : 'auto',
		right: resizer.includes('left') ? offsetX : 'auto',
		top: `calc(50% - ${offsetY})`,
	}
}

const getMediaIndicatorPosition = () => {
	const resizer = props.currentResizer
	const offset = getScaledOffset(8)

	return {
		left: resizer.includes('left') ? offset : 'auto',
		right: resizer.includes('right') ? offset : 'auto',
		top: resizer.includes('top') ? offset : 'auto',
		bottom: resizer.includes('bottom') ? offset : 'auto',
	}
}

const getPositionStyles = () => {
	if (props.type === 'text') {
		return getTextIndicatorPosition()
	}
	return getMediaIndicatorPosition()
}

const indicatorStyles = computed(() => {
	if (!props.currentResizer) return {}

	const scale = slideBounds.scale
	const positionStyles = getPositionStyles()

	return {
		position: 'absolute',
		zIndex: 100,
		fontSize: `${10 / scale}px`,
		borderRadius: `${6 / scale}px`,
		padding: `${4 / scale}px`,
		...positionStyles,
	}
})

const indicatorClasses = computed(() => {
	const isDark = isBackgroundColorDark(slide.value.background)
	return [isDark ? 'bg-white-overlay-600' : 'bg-gray-100']
})
</script>
