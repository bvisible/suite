<template>
	<div>
		<ResizeHandle
			v-for="resizeHandle in resizeHandles"
			v-show="handleVisibilityMap[resizeHandle]"
			:key="resizeHandle"
			:resizer="resizeHandle"
			:cursor="resizeCursor"
			@startResize="(e) => startResize(e, resizeHandle)"
			@resizeToFitContent="resizeToFitContent"
		/>

		<div
			v-show="currentResizer"
			:style="badgeStyles"
			class="backdrop-blur-sm opacity-80 text-2xs scale-90 text-black p-1"
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

const badgeBaseStyles = {
	position: 'absolute',
	zIndex: 100,
	borderRadius: '6px',
}

const badgeStyles = computed(() => {
	if (!currentResizer.value) return {}

	if (props.elementType == 'text') {
		return {
			...badgeBaseStyles,
			left: currentResizer.value.includes('right')
				? selectionBounds.width + 20 + 'px'
				: 'auto',
			right: currentResizer.value.includes('left')
				? selectionBounds.width + 20 + 'px'
				: 'auto',
			top: 'calc(50% - 8.5px)',
		}
	}

	return {
		...badgeBaseStyles,
		left: currentResizer.value.includes('left') ? '8px' : 'auto',
		right: currentResizer.value.includes('right') ? '8px' : 'auto',
		top: currentResizer.value.includes('top') ? '8px' : 'auto',
		bottom: currentResizer.value.includes('bottom') ? '8px' : 'auto',
	}
})

const resizeHandles = computed(() => {
	if (props.elementType === 'text') return ['resizer-left', 'resizer-right']
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

const handleDimensionChange = (delta) => {
	const ratio = selectionBounds.width / selectionBounds.height
	delta.top = (delta.top ?? 0) / ratio

	selectionBounds.left += delta.left / slideBounds.scale
	selectionBounds.top += delta.top / slideBounds.scale

	emit('updateElementWidth', delta.width || 0)
}

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
