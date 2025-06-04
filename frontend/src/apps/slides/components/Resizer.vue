<template>
	<div>
		<ResizeHandle
			v-for="resizeHandle in resizeHandles"
			v-show="resizeHandle.isVisible"
			:key="resizeHandle.direction"
			:direction="resizeHandle.direction"
			@startResize="(e) => startResize(e, resizeHandle.direction)"
			@resizeToFitContent="resizeToFitContent"
		/>

		<ResizeIndicator
			v-show="currentResizer"
			:type="elementType"
			:dimensions="selectionBounds"
			:indicatorStyles="indicatorStyles"
		/>
	</div>
</template>

<script setup>
import { computed, inject, watch } from 'vue'

import ResizeHandle from '@/components/ResizeHandle.vue'
import ResizeIndicator from '@/components/ResizeIndicator.vue'

import { selectionBounds, slideBounds, updateSelectionBounds } from '@/stores/slide'
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

const { dimensionDelta, currentResizer, startResize, resizeHandles, resizeCursor } = useResizer(
	props.elementType,
)

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

const handleDimensionChange = (delta) => {
	if (!delta.width) return

	const ratio = selectionBounds.width / selectionBounds.height
	delta.top = (delta.top ?? 0) / ratio

	const minWidth = props.elementType === 'text' ? 7 : 50
	if (delta.width + selectionBounds.width < minWidth) return

	updateSelectionBounds({
		left: selectionBounds.left + delta.left / slideBounds.scale,
		top: selectionBounds.top + delta.top / slideBounds.scale,
	})

	emit('updateElementWidth', delta.width / slideBounds.scale || 0)
}

const resizeToFitContent = () => {
	// create range of the text node within TextElement
	const target = props.elementDivRef
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
