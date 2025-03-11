<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div ref="target" :style="targetStyles">
		<div
			class="slide h-[540px] w-[960px] shadow-2xl"
			:class="!activeElementIds.length ? 'shadow-gray-400' : 'shadow-gray-300'"
			:style="slideStyles"
		>
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
	slideFocus,
	slide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
	slideRect,
	loadSlide,
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

const router = useRouter()

const props = defineProps({
	containerRef: Object,
})

const targetRef = useTemplateRef('target')
const guides = useTemplateRef('guides')

slideRect.value = useElementBounding(targetRef)

const { isDragging, dragTarget, movement } = useDragAndDrop()
const { isResizing, resizeTarget, resizeMode } = useResizer(activePosition, activeDimensions)
const { isPanningOrZooming, allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	props.containerRef,
	targetRef,
)

const showGuides = computed(() => activeElementIds.value.length && !isPanningOrZooming.value)

const scale = computed(() => {
	const matrix = transform.value.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

const targetStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
}))

const slideStyles = computed(() => ({
	backgroundColor: slide.value.background || 'white',
	cursor: isDragging.value ? 'move' : 'default',
	'--showEdgeOverlay': !activeElementIds.value.length ? 'block' : 'none',
}))

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	if (focusElementId.value) {
		slide.value.elements[focusElementId.value].content = document.querySelector(
			`[data-index="${focusElementId.value}"]`,
		).innerText
	}
	resetFocus()
	slideFocus.value = true
}

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
	if (e.target.classList.contains('slide')) {
		selectSlide(e)
	} else if (e.target == props.containerRef) {
		resetFocus()
		slideFocus.value = false
	}
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
			element.top += 2
			slide.value.elements[oldVal].content = document.querySelector(
				`[data-index="${oldVal}"]`,
			).innerText
		}
		if (newVal) {
			slide.value.elements[newVal].top -= 2
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

watch(
	() => pairElementId.value,
	(newVal, oldVal) => {
		if (oldVal) {
			slide.value.elements[oldVal].top += 2
		}
		if (newVal) {
			slide.value.elements[newVal].top -= 2
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
