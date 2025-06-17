<template>
	<div ref="slideContainer" class="flex size-full" @dragenter="showOverlay">
		<!-- when mounting place slide directly in the center of the visible container -->
		<!-- 1/2 width of viewport + 1/2 width of offset caused due to thinner navigation panel -->
		<div
			ref="target"
			:style="targetStyles"
			class="fixed top-[calc(50%-270px)] left-[calc(50%-512px)]"
		>
			<div ref="slideRef" :class="slideClasses" :style="slideStyles">
				<SelectionBox ref="selectionBox" @mousedown="(e) => handleMouseDown(e)" />

				<SnapGuides v-if="isDragging" :visibilityMap="visibilityMap" />

				<SlideElement
					v-for="element in slide.elements"
					:key="element.id"
					:element="element"
					:outline="getElementOutline(element)"
					:isDragging="isDragging"
					:data-index="element.id"
					@mousedown="(e) => handleMouseDown(e, element)"
					@dblclick="(e) => handleDoubleClick(e, element)"
				/>
			</div>
		</div>
	</div>

	<DropTargetOverlay v-show="mediaDragOver" @hideOverlay="hideOverlay" />

	<OverflowContentOverlay v-if="!activeElementIds.length" />
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, nextTick, onMounted, provide } from 'vue'
import { useResizeObserver } from '@vueuse/core'

import SnapGuides from '@/components/SnapGuides.vue'
import SelectionBox from '@/components/SelectionBox.vue'
import SlideElement from '@/components/SlideElement.vue'
import DropTargetOverlay from '@/components/DropTargetOverlay.vue'
import OverflowContentOverlay from '@/components/OverflowContentOverlay.vue'

import { presentation } from '@/stores/presentation'
import { slide, slideBounds, selectionBounds, updateSelectionBounds } from '@/stores/slide'
import {
	activeElementIds,
	activeElement,
	handleCopy,
	handlePaste,
	focusElementId,
	pairElementId,
	updateElementWidth,
} from '@/stores/element'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'
import { usePanAndZoom } from '@/utils/zoom'
import { useSnapping } from '@/utils/snap'

const props = defineProps({
	highlight: Boolean,
})

const slideContainerRef = useTemplateRef('slideContainer')
const slideTargetRef = useTemplateRef('target')
const slideRef = useTemplateRef('slideRef')
const selectionBoxRef = useTemplateRef('selectionBox')

const { isDragging, positionDelta, startDragging } = useDragAndDrop()

const { dimensionDelta, currentResizer, resizeCursor, startResize } = useResizer()

const { visibilityMap, updateGuides, disableMovement, getSnapDelta } = useSnapping(
	selectionBoxRef,
	slideRef,
)
const { allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	slideContainerRef,
	slideTargetRef,
)

const slideClasses = computed(() => {
	const classes = ['slide', 'h-[540px]', 'w-[960px]', 'shadow-2xl']

	const outlineClasses =
		props.highlight || mediaDragOver.value ? ['outline', 'outline-2', 'outline-blue-400'] : []
	const shadowClasses = activeElementIds.value.length ? ['shadow-gray-200'] : ['shadow-gray-400']

	return [...classes, outlineClasses, shadowClasses]
})

const targetStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
}))

const slideStyles = computed(() => ({
	backgroundColor: slide.value.background || 'white',
	'--showEdgeOverlay': !activeElementIds.value.length ? 'block' : 'none',
	cursor: isDragging.value ? 'move' : resizeCursor.value || 'default',
}))

const getElementOutline = (element) => {
	if (activeElementIds.value.concat([focusElementId.value]).includes(element.id)) {
		return 'primary'
	} else if (pairElementId.value === element.id) {
		return 'secondary'
	} else {
		return 'none'
	}
}

const mediaDragOver = ref(false)

const showOverlay = (e) => {
	e.preventDefault()
	mediaDragOver.value = true
}

const hideOverlay = () => {
	mediaDragOver.value = false
}

let dragTimeout, clickTimeout

const clearTimeouts = () => {
	clearTimeout(dragTimeout)
	clearTimeout(clickTimeout)
}

const triggerSelection = (e, id) => {
	if (id && !focusElementId.value && !activeElementIds.value.includes(id)) {
		activeElementIds.value = [id]
	}
}

const handleMouseUp = (e, id) => {
	clearTimeouts()

	pairElementId.value = null

	if (!isDragging.value) clickTimeout = setTimeout(() => triggerSelection(e, id), 100)
}

const triggerDrag = (e, id) => {
	const notEditable = id && focusElementId.value !== id
	const isMultiSelect = activeElementIds.value.length > 1
	const isNotInSelection = id && !activeElementIds.value.includes(id)

	// prevent drag if multiple are selected and id isn't in the selection
	if (isMultiSelect && isNotInSelection) return

	if (notEditable || isMultiSelect) {
		startDragging(e)

		if (id && !isMultiSelect && activeElementIds.value[0] !== id) {
			activeElementIds.value = [id]
			focusElementId.value = null
		}
	}
}

const handleMouseDown = (e, element) => {
	const id = element?.id

	// resume normal behavior if element is being edited
	if (id === focusElementId.value) return

	e.stopPropagation()
	e.preventDefault()

	// wait for click to be registered
	// if the click is not registered, it means the user is dragging
	dragTimeout = setTimeout(() => triggerDrag(e, id), 100)

	// if the click is registered ie. mouseup happens before dragTimeout
	// then consider it a selection instead of dragging
	e.target.addEventListener('mouseup', () => handleMouseUp(e, id), { once: true })
}

const makeTextEditable = (target, element) => {
	clearTimeouts()

	activeElementIds.value = []
	focusElementId.value = element.id

	nextTick(() => {
		target.focus()
	})
}

const handleDoubleClick = (e, element) => {
	if (element.type !== 'text') return

	makeTextEditable(e.target, element)
}

const scale = computed(() => {
	const matrix = transform.value?.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

const activeDiv = computed(() => {
	if (activeElementIds.value.length != 1) return null
	return document.querySelector(`[data-index="${activeElementIds.value[0]}"]`)
})

useResizeObserver(activeDiv, (entries) => {
	const entry = entries[0]
	const { width, height } = entry.contentRect

	// case:
	// when element dimensions are changed not by resizer
	// but by other updates on properties - font size, line height, letter spacing etc.
	updateSelectionBounds({
		width: width,
		height: height,
	})
})

const togglePanZoom = () => {
	allowPanAndZoom.value = !allowPanAndZoom.value
}

const getTotalPositionDelta = (delta) => {
	const snapDelta = getSnapDelta()

	return {
		left: delta.x + snapDelta.x,
		top: delta.y + snapDelta.y,
	}
}

const handlePositionChange = (delta) => {
	updateGuides()

	if (!disableMovement.value) {
		const totalDelta = getTotalPositionDelta(delta)
		updateSelectionBounds({
			left: selectionBounds.left + totalDelta.left / scale.value,
			top: selectionBounds.top + totalDelta.top / scale.value,
		})
	}
}

const applyAspectRatio = (offset) => {
	if (!offset) return 0
	const ratio = selectionBounds.width / selectionBounds.height
	return (offset ?? 0) / ratio
}

const validateMinWidth = (width) => {
	const minWidth = activeElement.value.type === 'text' ? 7 : 50
	return width + selectionBounds.width > minWidth
}

const handleDimensionChange = (delta) => {
	if (!delta.width || !validateMinWidth(delta.width)) return

	delta.top = applyAspectRatio(delta.top)

	updateSelectionBounds({
		left: selectionBounds.left + delta.left / slideBounds.scale,
		top: selectionBounds.top + delta.top / slideBounds.scale,
	})

	const newWidth = delta.width / slideBounds.scale || 0
	updateElementWidth(newWidth)
}

const updateSlideBounds = () => {
	const slideRect = slideRef.value.getBoundingClientRect()

	slideBounds.width = slideRect.width
	slideBounds.height = slideRect.height
	slideBounds.left = slideRect.left
	slideBounds.top = slideRect.top
	slideBounds.scale = scale.value
}

const handleSlideTransform = () => {
	// wait for the new transform to render before updating dimensions
	nextTick(() => {
		updateSlideBounds()
	})
}

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		selectionBoxRef.value.handleSelectionChange(newVal, oldVal)
	},
)

watch(
	() => transform.value,
	() => {
		if (!transform.value) return
		handleSlideTransform()
	},
)

watch(
	() => positionDelta.value,
	(delta) => {
		handlePositionChange(delta)
	},
)

watch(
	() => dimensionDelta.value,
	(delta) => {
		handleDimensionChange(delta)
	},
)

onMounted(() => {
	if (!slideRef.value) return

	updateSlideBounds()

	document.addEventListener('copy', handleCopy)
	document.addEventListener('paste', handlePaste)
})

provide('slideDiv', slideRef)
provide('slideContainerDiv', slideContainerRef)
provide('resizer', {
	currentResizer,
	startResize,
})

defineExpose({
	togglePanZoom,
})
</script>
