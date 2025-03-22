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
import { useElementBounding } from '@vueuse/core'

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
	slideDimensions,
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
} from '@/stores/element'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'
import { usePanAndZoom } from '@/utils/zoom'

const props = defineProps({
	highlight: Boolean,
})

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

const addDragAndResize = () => {
	let el = selectionBoxRef.value?.$el
	if (!el) return
	nextTick(() => {
		dragTarget.value = el
		const { left, top } = selectionBoxRef.value.getBoxBounds()
		setActivePosition({
			left: left + slideDimensions.left,
			top: top + slideDimensions.top,
		})
	})
	if (activeElementIds.value.length == 1) {
		resizeTarget.value = document.querySelector(`[data-index="${activeElementIds.value[0]}"]`)
		resizeMode.value = activeElements.value[0].type == 'text' ? 'width' : 'both'
	}
}

const removeDragAndResize = (val) => {
	setActivePosition(null)
	activeDimensions.value = null
	dragTarget.value = null
	resizeTarget.value = null
}

const updateFocus = (e) => {
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	selectSlide(e)
}

const updateSlideDimensions = () => {
	const slideRect = slideRef.value.getBoundingClientRect()

	slideDimensions.width = slideRect.width
	slideDimensions.height = slideRect.height
	slideDimensions.left = slideRect.left
	slideDimensions.top = slideRect.top
	slideDimensions.scale = scale.value
}

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		selectionBoxRef.value.handleSelectionChange(newVal, oldVal)
		if (newVal.length) {
			addDragAndResize()
		} else if (oldVal) {
			removeDragAndResize(oldVal)
		}
	},
)

watch(
	() => focusElementId.value,
	(newVal, oldVal) => {
		if (oldVal) {
			let element = slide.value.elements.find((el) => el.id == oldVal)
			element.content = document.querySelector(`[data-index="${oldVal}"]`).innerText
		}
	},
	{ immediate: true },
)

watch(
	() => presentation.data,
	() => {
		const currentSlide = presentation.data?.slides[slideIndex.value]
		if (!currentSlide) return
		loadSlide()
	},
	{ immediate: true },
)

const DELAY_COUNT = 15

const delayPositionUpdates = ref(0)

watch(
	() => movement.value,
	() => {
		if (!movement.value || !activePosition.value) return

		const { x, y } = movement.value

		const initialPosition = {
			dx: x / scale.value,
			dy: y / scale.value,
		}

		const snappedPosition = guides.value.getMovementBasedOnSnap(initialPosition)

		const didSnap =
			initialPosition.dx != snappedPosition.dx || initialPosition.dy != snappedPosition.dy

		if (!delayPositionUpdates.value) {
			updateActivePosition({
				dx: snappedPosition.dx,
				dy: snappedPosition.dy,
			})
			selectionBoxRef.value.setBoxBounds({
				left: activePosition.value.left - slideDimensions.left,
				top: activePosition.value.top - slideDimensions.top,
			})
		} else delayPositionUpdates.value -= 1

		if (didSnap) {
			delayPositionUpdates.value = DELAY_COUNT
		}
	},
)

watch(
	() => activeDimensions.value,
	(dimensions) => {
		if (!dimensions) return
		const id = activeElementIds.value[0]
		let element = slide.value.elements.find((el) => el.id == id)
		if (element && dimensions.width != element.width) {
			const newWidth = dimensions.width / scale.value
			element.width = newWidth
		}
		selectionBoxRef.value.setBoxBounds({
			width: dimensions.width,
			height: dimensions.height,
		})
	},
)

watch(
	() => transform.value,
	() => {
		if (!transform.value) return
		// wait for the new transform to render before updating dimensions
		nextTick(() => {
			updateSlideDimensions()
		})
	},
)

onMounted(() => {
	if (!slideRef.value) return
	updateSlideDimensions()
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
