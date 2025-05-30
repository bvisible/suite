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

		<ResizeIndicator
			v-show="currentResizer"
			:currentResizer="currentResizer"
			:type="elementType"
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

const handleDimensionChange = (delta) => {
	if (!currentResizer.value || !delta.width) return

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
