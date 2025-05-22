<template>
	<div>
		<ResizeHandle
			v-for="resizeHandle in resizeHandles"
			v-show="handleVisibilityMap[resizeHandle]"
			:key="resizeHandle"
			:direction="resizeHandle"
			:cursor="resizeCursor"
			@startResize="(e) => startResize(e, resizeHandle)"
			@resizeToFitContent="resizeToFitContent"
		/>

		<div
			v-show="currentResizer"
			:style="indicatorStyles"
			class="backdrop-blur-sm opacity-80 text-black"
			:class="
				isBackgroundColorDark(slide.background) ? 'bg-white-overlay-600' : 'bg-gray-100'
			"
		>
			<i v-if="elementType === 'text'"> {{ Math.round(selectionBounds.width) }}px </i>
			<template v-else>
				<i>{{ Math.round(selectionBounds.width) }}px</i> ×
				<i>{{ Math.round(selectionBounds.height) }}px</i>
			</template>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, watch } from 'vue'

import ResizeHandle from '@/components/ResizeHandle.vue'
import { isBackgroundColorDark } from '@/utils/color'

import { selectionBounds, slide, slideBounds } from '@/stores/slide'
import { useResizer } from '@/utils/resizer'

const props = defineProps({
	elementType: {
		type: String,
		required: true,
	},
	elementDivRef: {
		type: Object,
		default: null,
	},
})

const emit = defineEmits(['updateElementWidth'])

const element = defineModel('element', {
	type: Object,
	default: null,
})

const updateSlideCursor = inject('updateSlideCursor')

const { dimensionDelta, currentResizer, startResize } = useResizer()

const resizeCursor = computed(() => {
	switch (currentResizer.value) {
		case 'top-left':
			return 'nwse-resize'
		case 'top-right':
			return 'nesw-resize'
		case 'bottom-left':
			return 'nesw-resize'
		case 'bottom-right':
			return 'nwse-resize'
		case 'left':
		case 'right':
			return 'ew-resize'
		default:
			return 'default'
	}
})

const resizeHandles = computed(() => {
	if (props.elementType === 'text') return ['left', 'right']
	else return ['top-left', 'top-right', 'bottom-left', 'bottom-right']
})

const isResizeHandleVisible = (resizer) => {
	if (!currentResizer.value) return true
	return currentResizer.value === resizer
}

const handleVisibilityMap = computed(() => {
	return resizeHandles.value.reduce((acc, resizer) => {
		acc[resizer] = isResizeHandleVisible(resizer)
		return acc
	}, {})
})

const getTextIndicatorPosition = () => {
	const scale = slideBounds.scale
	const offset = `${selectionBounds.width + 20 / scale}px`

	return {
		left: currentResizer.value.includes('right') ? offset : 'auto',
		right: currentResizer.value.includes('left') ? offset : 'auto',
		top: `calc(50% - ${12 / scale}px)`,
	}
}

const getMediaIndicatorPosition = () => {
	const scale = slideBounds.scale
	const offset = `${8 / scale}px`

	return {
		left: currentResizer.value.includes('left') ? offset : 'auto',
		right: currentResizer.value.includes('right') ? offset : 'auto',
		top: currentResizer.value.includes('top') ? offset : 'auto',
		bottom: currentResizer.value.includes('bottom') ? offset : 'auto',
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

const handleDimensionChange = (delta) => {
	if (!currentResizer.value || !delta.width) return

	const ratio = selectionBounds.width / selectionBounds.height
	delta.top = (delta.top ?? 0) / ratio

	const minWidth = props.elementType === 'text' ? 7 : 50
	if (delta.width + selectionBounds.width < minWidth) return

	selectionBounds.left += delta.left / slideBounds.scale
	selectionBounds.top += delta.top / slideBounds.scale

	emit('updateElementWidth', delta.width / slideBounds.scale || 0)
}

const resizeToFitContent = () => {
	// create range of the text node within TextElement
	const target = props.elementDivRef?.value
	const range = document.createRange()
	const textNode = target.firstChild
	const originalWidth = target.offsetWidth
	range.selectNodeContents(textNode)

	// find out width of text content
	const textWidth = range.getBoundingClientRect().width
	handleDimensionChange({ width: textWidth - originalWidth + 5 })
}

watch(
	() => dimensionDelta.value,
	(delta) => {
		handleDimensionChange(delta)
	},
)

watch(
	() => currentResizer.value,
	(resizer) => {
		updateSlideCursor(resizeCursor.value)
	},
)
</script>
