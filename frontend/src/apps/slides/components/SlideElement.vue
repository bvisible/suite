<template>
	<div :style="elementStyle">
		<component :is="getDynamicComponent(element.type)" :element="element" />

		<Resizer
			v-for="resizer in resizeHandles"
			v-show="isResizerVisible(resizer)"
			:key="resizer"
			:resizer="resizer"
			:cursor="resizeCursor"
			@startResize="(e) => startResize(e, resizer)"
			@resizeToFitContent="resizeToFitContent"
		/>

		<div
			v-show="currentResizer"
			:style="badgeStyles"
			class="bg-white-overlay-500 backdrop-blur-sm opacity-90 text-2xs text-black p-1"
		>
			<i>{{ Math.round(selectionBounds.width) }}px</i> ×
			<i>{{ Math.round(selectionBounds.height) }}px</i>
		</div>
	</div>
</template>

<script setup>
import { computed, watch } from 'vue'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'
import VideoElement from '@/components/VideoElement.vue'
import Resizer from '@/components/Resizer.vue'

import { useResizer } from '@/utils/resizer'
import { selectionBounds, updateSelectionBounds } from '@/stores/slide'
import { activeElementIds } from '@/stores/element'

const { dimensionDelta, currentResizer, startResize } = useResizer()

const props = defineProps({
	outline: {
		type: String,
		default: 'none',
	},
})

const emit = defineEmits(['updateSlideCursor'])

const element = defineModel('element', {
	type: Object,
	default: null,
})

const outline = computed(() => {
	switch (props.outline) {
		case 'primary':
			return '#70B6F0 solid 2px'
		case 'secondary':
			return '#70b6f080 solid 2px'
		default:
			return props.outline
	}
})

const elementStyle = computed(() => ({
	position: activeElementIds.value.includes(element.value.id) ? 'absolute' : 'fixed',
	width: `${element.value.width}px` || 'auto',
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	outline: outline.value,
	boxSizing: 'border-box',
}))

const getDynamicComponent = (type) => {
	switch (type) {
		case 'image':
			return ImageElement
		case 'video':
			return VideoElement
		default:
			return TextElement
	}
}

const resizeHandles = computed(() => {
	if (!element.value) return []
	if (element.value.type === 'text') return ['resizer-left', 'resizer-right']
	else
		return [
			'resizer-top-left',
			'resizer-top-right',
			'resizer-bottom-left',
			'resizer-bottom-right',
		]
})

const resizeCursor = computed(() => {
	switch (currentResizer.value) {
		case 'resizer-top-left':
			return 'nwse-resize'
		case 'resizer-top-right':
			return 'nesw-resize'
		case 'resizer-bottom-left':
			return 'nesw-resize'
		case 'resizer-bottom-right':
			return 'nwse-resize'
		case 'resizer-left':
		case 'resizer-right':
			return 'ew-resize'
		default:
			return 'default'
	}
})

const updateElementWidth = (deltaWidth) => {
	if (element.value.width) {
		element.value.width += deltaWidth
	} else {
		const elementDiv = document.querySelector(`[data-index="${element.value.id}"]`)
		const width = elementDiv.getBoundingClientRect().width

		element.value.width = width + deltaWidth
	}
}

const handleDimensionChange = (delta) => {
	const ratio = selectionBounds.width / selectionBounds.height
	delta.top = (delta.top ?? 0) / ratio

	updateSelectionBounds(delta)

	updateElementWidth(delta.width)
}

const isResizerVisible = (resizer) => {
	if (!activeElementIds.value.length) return false
	if (activeElementIds.value[0] != element.value.id) return false
	if (!currentResizer.value) return true
	return currentResizer.value === resizer
}

const resizeToFitContent = () => {
	// create range of the text node within TextElement
	const target = document.querySelector(`[data-index="${element.value.id}"]`)
	if (!target) return
	const range = document.createRange()
	const textNode = target.firstChild
	const originalWidth = target.offsetWidth
	range.selectNodeContents(textNode)

	// find out width of text content
	const textWidth = range.getBoundingClientRect().width
	// auto resize width of TextElement to fit content with some padding
	handleDimensionChange({
		width: textWidth - originalWidth + 5,
	})
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
		emit('updateSlideCursor', resizeCursor.value)
	},
)

const badgeBaseStyles = {
	position: 'absolute',
	zIndex: 100,
	borderRadius: '6px',
}

const badgeStyles = computed(() => {
	if (!currentResizer.value) return {}
	return {
		...badgeBaseStyles,
		left: currentResizer.value.includes('left') ? '8px' : 'auto',
		right: currentResizer.value.includes('right') ? '8px' : 'auto',
		top: currentResizer.value.includes('top') ? '8px' : 'auto',
		bottom: currentResizer.value.includes('bottom') ? '8px' : 'auto',
	}
})
</script>
