<template>
	<div ref="slideContainer" class="flex w-full h-full">
		<!-- when mounting place slide directly in the center of the visible container -->
		<!-- 1/2 width of viewport + 1/2 width of offset caused due to thinner navigation panel -->
		<div
			ref="target"
			:style="targetStyles"
			class="fixed top-[calc(50%-270px)] left-[calc(50%-512px)]"
		>
			<div ref="slideRef" :class="slideClasses" :style="slideStyles">
				<SelectionBox ref="selectionBox" @updateFocus="updateFocus" :bounds="bounds" />

				<!-- <AlignmentGuides
					v-if="showGuides"
					ref="guides"
					:selectedRef="selectionBoxRef.$el"
				/> -->

				<Guides v-if="isDragging" :visibilityMap="visibilityMap" />

				<SlideElement
					v-for="element in slide.elements"
					:key="element.id"
					:element="element"
					:data-index="element.id"
					@mousedown="(e) => handleMouseDown(e, element)"
					@dblclick="(e) => handleDoubleClick(e, element)"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef, nextTick, onMounted, provide, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useResizeObserver } from '@vueuse/core'

import SlideElement2 from '@/components/SlideElement2.vue'
// import AlignmentGuides from '@/components/AlignmentGuides.vue'
import Guides from '@/components/Guides.vue'
import SelectionBox from './SelectionBox.vue'

import { presentation } from '@/stores/presentation'
import { slide, selectSlide, slideBounds } from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElements,
	activeElement,
	activeElementIds,
	updateActivePosition,
	setActivePosition,
	resizeElement,
	handleCopy,
	handlePaste,
	focusElementId,
} from '@/stores/element'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'
import { usePanAndZoom } from '@/utils/zoom'
import { useSnapping } from '@/utils/snap'

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

const { isDragging, dragMovement, startDragging } = useDragAndDrop()
const { isResizing, resizeDiffs, updateResizers } = useResizer()
const { visibilityMap, updateGuides, disableMovement, getSnapMovement } = useSnapping(
	selectionBoxRef,
	slideRef,
)
const { isPanningOrZooming, allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	slideContainerRef,
	slideTargetRef,
)

const slideClasses = computed(() => {
	const classes = ['slide', 'h-[540px]', 'w-[960px]', 'shadow-2xl']

	const outlineClasses = props.highlight ? ['outline', 'outline-2', 'outline-blue-400'] : []
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

const handleSelectionChange = (newSelection, oldSelection) => {
	selectionBoxRef.value.handleSelectionChange(newSelection, oldSelection)
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
	bounds.width = width
	bounds.height = height
})

const togglePanZoom = () => {
	allowPanAndZoom.value = !allowPanAndZoom.value
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
		if (newVal.length < 2) {
			const targetElement = document.querySelector(`[data-index="${newVal[0]}"]`)
			const resizeMode = activeElement.value?.type == 'text' ? 'width' : 'both'
			updateResizers(targetElement, resizeMode)
		}
		handleSelectionChange(newVal, oldVal)
	},
)

watch(
	() => transform.value,
	() => {
		if (!transform.value) return
		handleSlideTransform()
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
provide('isDragging', isDragging)

defineExpose({
	togglePanZoom,
})

const bounds = reactive({
	left: 0,
	top: 0,
	width: 0,
	height: 0,
})

const addToActiveElements = (id) => {
	if (!activeElementIds.value.includes(id) && focusElementId.value != id) {
		activeElementIds.value = [...activeElementIds.value, id]
	}
}

let dragTimeout

const handleMouseDown = (e, element) => {
	if (focusElementId.value == element.id) return

	dragTimeout = setTimeout(() => {
		addToActiveElements(element.id)

		startDragging(e)
	}, 100)

	e.target.addEventListener('mouseup', () => {
		clearTimeout(dragTimeout)

		addToActiveElements(element.id)
	})
}

const handleDoubleClick = (e, element) => {
	if (element.type !== 'text') return
	clearTimeout(dragTimeout)
	activeElementIds.value = []
	focusElementId.value = element.id
}

const moveElement = (movement) => {
	bounds.left += movement.x / scale.value
	bounds.top += movement.y / scale.value
}

watch(
	() => dragMovement.value,
	(movement) => {
		updateGuides()

		let totalMovement = {
			x: 0,
			y: 0,
		}

		if (!disableMovement.value) {
			totalMovement.x += movement.x
			totalMovement.y += movement.y

			const snapMovement = getSnapMovement()

			totalMovement.x += snapMovement.x
			totalMovement.y += snapMovement.y

			moveElement(totalMovement)
		}
	},
)

watch(
	() => resizeDiffs.value,
	(diffs) => {
		bounds.width += diffs.width / scale.value
		bounds.left += diffs.left / scale.value
		bounds.top += diffs.top / scale.value

		activeElement.value.width += diffs.width / scale.value
	},
)
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
