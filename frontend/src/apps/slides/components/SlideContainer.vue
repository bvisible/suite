<template>
	<div ref="slideContainer" class="slideContainer flex items-center justify-center w-full h-full">
		<div ref="target" :style="targetStyles">
			<div ref="slideRef" :class="slideClasses" :style="slideStyles">
				<SelectionBox ref="selectionBox" @updateFocus="updateFocus" />

				<AlignmentGuides
					v-if="showGuides"
					ref="guides"
					:selectedRef="selectionBoxRef.$el"
				/>

				<SlideElement
					v-for="element in slide.elements"
					:key="element.id"
					:element="element"
					:data-index="element.id"
				/>
			</div>

			<!-- Slide Actions -->
			<div class="fixed -bottom-12 right-0 cursor-pointer p-3 flex items-center gap-4">
				<Trash size="14" class="text-gray-800 stroke-[1.5]" @click="deleteSlide" />
				<Copy size="14" class="text-gray-800 stroke-[1.5]" @click="duplicateSlide" />
				<SquarePlus
					size="14"
					class="text-gray-800 stroke-[1.5]"
					@click="insertSlide(slideIndex + 1)"
				/>
			</div>
		</div>
	</div>

	<!-- Media Drag Overlay -->
	<div
		v-show="highlight"
		class="bg-blue-400 opacity-10 z-15 w-full h-full fixed top-0 left-0"
	></div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, nextTick, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { useElementBounding, useResizeObserver } from '@vueuse/core'

import { Trash, Copy, SquarePlus } from 'lucide-vue-next'
import SlideElement from '@/components/SlideElement.vue'
import AlignmentGuides from '@/components/AlignmentGuides.vue'
import SelectionBox from './SelectionBox.vue'

import { presentation } from '@/stores/presentation'
import {
	slideIndex,
	slide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
	loadSlide,
	selectSlide,
	getSlideThumbnail,
	slideBounds,
} from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElements,
	activeElementIds,
	focusElementId,
	pairElementId,
	resetFocus,
	updateActivePosition,
	setActivePosition,
	resizeElement,
} from '@/stores/element'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'
import { usePanAndZoom } from '@/utils/zoom'

const props = defineProps({
	highlight: Boolean,
})

let recentlySnapped = false
let snapTimer = null

const router = useRouter()

const slideContainerRef = useTemplateRef('slideContainer')
const slideTargetRef = useTemplateRef('target')
const slideRef = useTemplateRef('slideRef')
const selectionBoxRef = useTemplateRef('selectionBox')
const guides = useTemplateRef('guides')

const { isDragging, dragTarget, movement } = useDragAndDrop()
const { isResizing, resizeTarget, resizeMode } = useResizer(activePosition, activeDimensions)
const { isPanningOrZooming, allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	slideContainerRef,
	slideTargetRef,
)

const delayPositionUpdates = ref(0)

const slideClasses = computed(() => {
	const classes = ['slide', 'h-[540px]', 'w-[960px]', 'shadow-2xl']

	const outlineClasses = props.highlight ? ['outline', 'outline-1.5', 'outline-blue-400'] : []
	const shadowClasses = activeElementIds.value.length ? ['shadow-gray-200'] : ['shadow-gray-400']
	const cursorClasses = isDragging.value ? ['cursor-move'] : ['cursor-default']

	return [...classes, outlineClasses, shadowClasses, cursorClasses]
})

const targetStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
}))

const slideStyles = computed(() => ({
	backgroundColor: slide.value.background || 'white',
	'--showEdgeOverlay': !activeElementIds.value.length ? 'block' : 'none',
}))

const showGuides = computed(() => activeElementIds.value.length && !isPanningOrZooming.value)

const scale = computed(() => {
	const matrix = transform.value?.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

const updateFocus = (e) => {
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	selectSlide(e)
}

const updateSlideBounds = () => {
	const slideRect = slideRef.value.getBoundingClientRect()

	slideBounds.width = slideRect.width
	slideBounds.height = slideRect.height
	slideBounds.left = slideRect.left
	slideBounds.top = slideRect.top
	slideBounds.scale = scale.value
}

const handleDimensionChange = (dimensions) => {
	const elementId = activeElementIds.value[0]

	// update element dimensions in slide object
	resizeElement(elementId, dimensions)
}

const initDraggable = () => {
	let el = selectionBoxRef.value?.$el
	if (!el) return

	// enable dragging on the selected box
	dragTarget.value = el

	// set initial position of the selection box
	const { left, top } = selectionBoxRef.value.getBoxBounds()
	setActivePosition({
		left: left + slideBounds.left,
		top: top + slideBounds.top,
	})
}

const initResizer = (element) => {
	// enable resizing on the selected element
	resizeTarget.value = document.querySelector(`[data-index="${element.id}"]`)

	// set initial dimensions of the element
	resizeMode.value = element.type == 'text' ? 'width' : 'both'
}

const addDragAndResize = () => {
	// if only one element is selected, enable resizing
	if (activeElementIds.value.length == 1) {
		initResizer(activeElements.value[0])
	}

	nextTick(() => {
		initDraggable()
	})
}

const removeDragAndResize = () => {
	setActivePosition(null)
	activeDimensions.value = null
	dragTarget.value = null
	resizeTarget.value = null
}

const getPositionChange = (movement) => {
	return {
		dx: movement.x / scale.value,
		dy: movement.y / scale.value,
	}
}

const hasSnapped = (positionChange, snappedPositionChange) => {
	return (
		positionChange.dx != snappedPositionChange.dx ||
		positionChange.dy != snappedPositionChange.dy
	)
}

const applyMovement = (positionChange) => {
	// move the element to the new position
	updateActivePosition({
		dx: positionChange.dx,
		dy: positionChange.dy,
	})

	// update selection box position to match the element
	selectionBoxRef.value.setBoxBounds({
		left: activePosition.value.left - slideBounds.left,
		top: activePosition.value.top - slideBounds.top,
	})
}

const handlePositionChange = (movement) => {
	// get change in position - scaled
	const positionChange = getPositionChange(movement)

	// get change in position - possible snaps
	const snapPositionChange = guides.value.getMovementBasedOnSnap(positionChange)

	const isElementSnapped = hasSnapped(positionChange, snapPositionChange)

	if (!recentlySnapped) {
		requestAnimationFrame(() => {
			applyMovement(snapPositionChange)
		})
	}

	if (isElementSnapped) {
		recentlySnapped = true
		clearTimeout(snapTimer)
		snapTimer = setTimeout(() => {
			recentlySnapped = false
		}, 300)
	}
}

const handleSelectionChange = (newSelection, oldSelection) => {
	selectionBoxRef.value.handleSelectionChange(newSelection, oldSelection)
	if (newSelection.length) {
		addDragAndResize()
	} else if (oldSelection) {
		removeDragAndResize()
	}
}

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
	selectionBoxRef.value.setBoxBounds({
		width: width,
		height: height,
	})
})

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		handleSelectionChange(newVal, oldVal)
	},
)

watch(
	() => movement.value,
	(movement) => {
		if (!movement || !activePosition.value) return
		handlePositionChange(movement)
	},
)

watch(
	() => activeDimensions.value,
	(dimensions) => {
		if (!dimensions) return
		handleDimensionChange(dimensions)
	},
)

watch(
	() => transform.value,
	() => {
		if (!transform.value) return
		// wait for the new transform to render before updating dimensions
		nextTick(() => {
			updateSlideBounds()

			// set initial position of the selection box after zooming / panning
			const { left, top } = selectionBoxRef.value.getBoxBounds()
			setActivePosition({
				left: left + slideBounds.left,
				top: top + slideBounds.top,
			})
		})
	},
)

onMounted(() => {
	if (!slideRef.value) return
	updateSlideBounds()
})

provide('slideDiv', slideRef)
provide('slideContainerDiv', slideContainerRef)
</script>

<style src="../assets/styles/resizer.css"></style>

<style>
.slide::after {
	content: '';
	display: var(--showEdgeOverlay, none);
	width: 100%;
	height: 100%;
	position: absolute;
	background: transparent;
	pointer-events: none;
	box-shadow: 0 0 5000px 500px rgba(255, 255, 255, 0.6);
}
</style>
