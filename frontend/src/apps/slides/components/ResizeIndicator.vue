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

const getTextIndicatorPosition = () => {
	const scale = slideBounds.scale
	const offset = `${selectionBounds.width + 20 / scale}px`

	return {
		left: props.currentResizer.includes('right') ? offset : 'auto',
		right: props.currentResizer.includes('left') ? offset : 'auto',
		top: `calc(50% - ${12 / scale}px)`,
	}
}

const getMediaIndicatorPosition = () => {
	const scale = slideBounds.scale
	const offset = `${8 / scale}px`

	return {
		left: props.currentResizer.includes('left') ? offset : 'auto',
		right: props.currentResizer.includes('right') ? offset : 'auto',
		top: props.currentResizer.includes('top') ? offset : 'auto',
		bottom: props.currentResizer.includes('bottom') ? offset : 'auto',
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
