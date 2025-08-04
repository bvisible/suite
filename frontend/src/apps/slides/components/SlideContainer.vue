<template>
	<div ref="slideContainer" class="flex size-full" @dragenter="showOverlay">
		<!-- when mounting place slide directly in the center of the visible container -->
		<!-- 1/2 width of viewport + 1/2 width of offset caused due to thinner navigation panel -->
		<div ref="slideRef" :style="slideStyles" :class="slideClasses">
			<SelectionBox ref="selectionBox" @mousedown="(e) => handleMouseDown(e)" />

			<SnapGuides :isDragging="isDragging" :visibilityMap="visibilityMap" />

			<SlideElement
				v-for="element in slide.elements"
				:key="element.id"
				:element
				:elementOffset
				:isDragging
				:data-index="element.id"
				:outline="getElementOutline(element)"
				@mousedown="(e) => handleMouseDown(e, element)"
				@clearTimeouts="clearTimeouts"
			/>
		</div>
		<DropTargetOverlay v-show="mediaDragOver" @hideOverlay="hideOverlay" />
		<OverflowContentOverlay />
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, nextTick, onMounted, provide, reactive } from 'vue'
import { useResizeObserver } from '@vueuse/core'

import SnapGuides from '@/components/SnapGuides.vue'
import SelectionBox from '@/components/SelectionBox.vue'
import SlideElement from '@/components/SlideElement.vue'
import DropTargetOverlay from '@/components/DropTargetOverlay.vue'
import OverflowContentOverlay from '@/components/OverflowContentOverlay.vue'

import {
	slide,
	slideBounds,
	selectionBounds,
	updateSelectionBounds,
	setSlideRef,
} from '@/stores/slide'
import {
	activeElementIds,
	activeElement,
	handleCopy,
	handlePaste,
	focusElementId,
	pairElementId,
	updateElementWidth,
} from '@/stores/element'

import { useDragAndDrop } from '@/composables/useDragAndDrop'
import { useResizer } from '@/composables/useResizer'
import { usePanAndZoom } from '@/composables/usePanAndZoom'
import { useSnapping } from '@/composables/useSnapping'

const props = defineProps({
	highlight: Boolean,
})

const slideContainerRef = useTemplateRef('slideContainer')
const slideRef = useTemplateRef('slideRef')
const selectionBoxRef = useTemplateRef('selectionBox')

const { isDragging, positionDelta, startDragging } = useDragAndDrop()

const { dimensionDelta, currentResizer, resizeCursor, startResize } = useResizer()

const { visibilityMap, resistanceMap, handleSnapping } = useSnapping(selectionBoxRef, slideRef)

const { allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(slideContainerRef, slideRef)

const slideClasses = computed(() => {
	const classes = [
		'absolute',
		'left-[calc(50%-512px)]',
		'top-[calc(50%-270px)]',
		'h-[540px]',
		'w-[960px]',
		'shadow-2xl',
		'shadow-gray-400',
	]

	const outlineClasses =
		props.highlight || mediaDragOver.value ? ['outline', 'outline-2', 'outline-blue-400'] : []

	return [...classes, outlineClasses]
})

const slideStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
	backgroundColor: slide.value.background || '#ffffff',
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
	if (id) {
		if (!activeElementIds.value.includes(id)) {
			activeElementIds.value = [id]
			focusElementId.value = null
		} else if (activeElement.value?.type == 'text') {
			focusElementId.value = id
		}
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

	e.stopPropagation()
	e.preventDefault()

	// wait for click to be registered
	// if the click is not registered, it means the user is dragging
	dragTimeout = setTimeout(() => triggerDrag(e, id), 100)

	// if the click is registered ie. mouseup happens before dragTimeout
	// then consider it a selection instead of dragging
	e.target.addEventListener('mouseup', () => handleMouseUp(e, id), { once: true })
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

const applyResistance = (axis, delta) => {
	const scaledThreshold = (0.02 * selectionBounds.width) / slideBounds.scale

	const escapeDelta = Math.max(2, Math.min(5, scaledThreshold))

	let useResistance = false
	let pullDelta = null

	if (axis == 'X') {
		useResistance = resistanceMap.left || resistanceMap.right || resistanceMap.centerY
		pullDelta = delta.x
	} else if (axis == 'Y') {
		useResistance = resistanceMap.top || resistanceMap.bottom || resistanceMap.centerX
		pullDelta = delta.y
	}

	return useResistance && Math.abs(pullDelta) < escapeDelta
}

const getTotalPositionDelta = (delta) => {
	const snapDelta = handleSnapping()

	const left = snapDelta.x || delta.x
	const top = snapDelta.y || delta.y

	return {
		left: applyResistance('X', delta) ? 0 : left,
		top: applyResistance('Y', delta) ? 0 : top,
	}
}

const elementOffset = reactive({
	left: 0,
	top: 0,
})

const handlePositionChange = (delta) => {
	const totalDelta = getTotalPositionDelta(delta)

	elementOffset.left += totalDelta.left / scale.value
	elementOffset.top += totalDelta.top / scale.value

	updateSelectionBounds({
		left: selectionBounds.left + totalDelta.left / scale.value,
		top: selectionBounds.top + totalDelta.top / scale.value,
	})
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

	setSlideRef(slideRef.value)

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

watch(
	() => isDragging.value,
	(isDragging) => {
		if (!isDragging) {
			requestAnimationFrame(() => {
				activeElementIds.value.forEach((id) => {
					const element = slide.value.elements.find((el) => el.id === id)
					if (element) {
						element.left += elementOffset.left
						element.top += elementOffset.top
					}
				})
				elementOffset.left = 0
				elementOffset.top = 0
			})
		}
	},
)
</script>
