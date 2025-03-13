<template>
	<div ref="slideContainer" class="slideContainer flex items-center justify-center w-full h-full">
		<div ref="target" :style="targetStyles">
			<div ref="slideRef" :class="slideClasses" :style="slideStyles">
				<SelectionBox @updateFocus="updateFocus" :scale="scale" />

				<AlignmentGuides ref="guides" v-if="showGuides" :scale="scale" />

				<component
					ref="element"
					v-for="(element, index) in slide.elements"
					:key="index"
					:is="SlideElement"
					:element="element"
					:data-index="index"
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
import { ref, computed, watch, useTemplateRef, nextTick } from 'vue'
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
	slideRect,
	loadSlide,
	selectSlide,
	getSlideThumbnail,
} from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElements,
	activeElementIds,
	focusElementId,
	pairElementId,
	resetFocus,
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
const guides = useTemplateRef('guides')

slideRect.value = useElementBounding(slideRef)

const { isDragging, dragTarget, movement } = useDragAndDrop()
const { isResizing, resizeTarget, resizeMode } = useResizer(activePosition, activeDimensions)
const { isPanningOrZooming, allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	slideContainerRef,
	slideTargetRef,
)

const slideClasses = computed(() => {
	const classes = ['slide', 'h-[540px]', 'w-[960px]', 'shadow-2xl']

	const outlineClasses = props.highlight ? ['outline', 'outline-1.5', 'outline-blue-400'] : []
	const shadowClasses = activeElementIds.value.length ? ['shadow-gray-300'] : []
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
	let el = document.querySelector('.groupDiv')
	if (!el) return
	nextTick(() => {
		dragTarget.value = el
	})
	if (activeElementIds.value.length == 1) {
		resizeTarget.value = document.querySelector(`[data-index="${activeElementIds.value[0]}"]`)
		resizeMode.value = activeElements.value[0].type == 'text' ? 'width' : 'both'
	}
}

const removeDragAndResize = (val) => {
	activePosition.value = null
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

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		if (newVal.length) {
			addDragAndResize()
		} else if (oldVal) {
			removeDragAndResize(oldVal)

			nextTick(async () => {
				slide.value.thumbnail = await getSlideThumbnail()
			})
		}
	},
	{ immediate: true },
)

watch(
	() => focusElementId.value,
	(newVal, oldVal) => {
		if (oldVal) {
			let element = slide.value.elements[oldVal]
			slide.value.elements[oldVal].content = document.querySelector(
				`[data-index="${oldVal}"]`,
			).innerText
		}
	},
	{ immediate: true },
)

watch(
	() => presentation.data,
	() => {
		const currentSlide = presentation.data?.slides[slideIndex.value]
		if (!currentSlide) return
		loadSlide(currentSlide)
	},
	{ immediate: true },
)

watch(
	() => movement.value,
	() => {
		if (!movement.value || !activePosition.value) return

		const { x, y } = movement.value

		guides.value.updateElementPosition(x / scale.value, y / scale.value)
	},
	{ immediate: true },
)

watch(
	() => activeDimensions.value,
	(dimensions) => {
		if (!dimensions) return
		let element = slide.value.elements[activeElementIds.value[0]]
		if (element && dimensions.width != element.width) {
			const newWidth = dimensions.width / scale.value
			element.width = newWidth
		}
	},
	{ immediate: true },
)

defineExpose({
	guides,
})
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
