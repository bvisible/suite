<template>
	<div :style="elementStyle">
		<Resizer
			v-for="resizer in resizeHandles"
			v-show="isResizerVisible(resizer)"
			:key="resizer"
			:resizer="resizer"
			@startResize="(e) => startResize(e, resizer)"
		/>

		<component :is="getDynamicComponent(element.type)" :element="element" />
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

	delta.top /= ratio

	updateSelectionBounds(delta)

	updateElementWidth(delta.width)
}

const isResizerVisible = (resizer) => {
	if (!activeElementIds.value.length) return false
	if (activeElementIds.value[0] != element.value.id) return false
	if (!currentResizer.value) return true
	return currentResizer.value === resizer
}

watch(
	() => dimensionDelta.value,
	(delta) => {
		handleDimensionChange(delta)
	},
)
</script>
