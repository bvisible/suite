<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div v-if="inSlideShow">
		<Transition
			@before-enter="beforeSlideEnter"
			@enter="slideEnter"
			@before-leave="beforeSlideLeave"
			@leave="slideLeave"
		>
			<div
				ref="target"
				class="slide h-[540px] w-[960px] drop-shadow-xl"
				:style="slideStyles"
				@click="handleSlideClick"
				:key="slideIndex"
			>
				<component
					ref="element"
					v-for="(element, index) in slide.elements"
					:key="index"
					:is="SlideElement"
					:element="element"
					:data-index="index"
				/>
			</div>
		</Transition>
	</div>
	<div
		v-else
		ref="target"
		class="slide h-[540px] w-[960px] drop-shadow-xl"
		:style="slideStyles"
		@click="handleSlideClick"
	>
		<ElementAlignmentGuides v-if="showGuides" :scale="scale" />

		<div class="fixed -bottom-12 right-0 cursor-pointer p-3 flex items-center gap-4">
			<Trash size="14" :strokeWidth="1.5" class="text-gray-800" @click="deleteSlide" />
			<Copy size="14" :strokeWidth="1.5" class="text-gray-800" @click="duplicateSlide" />
			<SquarePlus
				size="14"
				:strokeWidth="1.5"
				class="text-gray-800"
				@click="insertSlide(slideIndex)"
			/>
		</div>

		<component
			ref="element"
			v-for="(element, index) in slide.elements"
			:key="index"
			:is="SlideElement"
			:element="element"
			:data-index="index"
		/>
	</div>
</template>

<script setup>
import { ref, computed, watch, useTemplateRef } from 'vue'
import { useElementBounding } from '@vueuse/core'

import { Trash, Copy, SquarePlus } from 'lucide-vue-next'
import SlideElement from '@/components/SlideElement.vue'
import ElementAlignmentGuides from '@/components/ElementAlignmentGuides.vue'

import { presentation, inSlideShow, applyReverseTransition } from '@/stores/presentation'
import {
	slideIndex,
	slideFocus,
	slide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
	slideRect,
} from '@/stores/slide'
import {
	activePosition,
	activeDimensions,
	activeElement,
	activeElementId,
	focusElementId,
	resetFocus,
} from '@/stores/element'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'
import { usePanAndZoom } from '@/utils/zoom'

const props = defineProps({
	containerRef: Object,
	slideCursor: String,
})

const targetRef = useTemplateRef('target')

const { isDragging, dragTarget } = useDragAndDrop(activePosition)
const { isResizing, resizeTarget, resizeMode } = useResizer(activePosition, activeDimensions)
const { isPanningOrZooming, allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(
	props.containerRef,
	targetRef,
)

const transition = ref('none')
const opacity = ref(1)

const showGuides = computed(
	() => activeElement.value && activeElementId.value != null && !isPanningOrZooming.value,
)

const slideStyles = computed(() => {
	if (!presentation.data) return
	return {
		backgroundColor: presentation.data.slides[slideIndex.value]?.background || 'white',
		cursor: inSlideShow.value ? props.slideCursor : isDragging.value ? 'move' : 'default',
		transition: transition.value,
		transformOrigin: transformOrigin.value,
		transform: transform.value,
		opacity: opacity.value,
	}
})

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	if (activeElement.value && focusElementId.value) {
		activeElement.content = document.querySelector(
			`[data-index="${focusElementId.value}"]`,
		).innerText
	}
	resetFocus()
	slideFocus.value = true
}

const handleSlideClick = (e) => {
	e.stopPropagation()
	if (e.target != targetRef.value) return
	if (inSlideShow.value) {
		slideIndex.value += 1
		return
	} else selectSlide(e)
}

const addDragAndResize = () => {
	let el = document.querySelector(`[data-index="${activeElementId.value}"]`)
	if (!el || !activeElement.value) return
	dragTarget.value = el
	resizeTarget.value = el
	resizeMode.value = activeElement.value.type == 'text' ? 'width' : 'both'

	const elementRect = el.getBoundingClientRect()
	activePosition.value = {
		top: elementRect.top,
		left: elementRect.left,
	}
}

const removeDragAndResize = () => {
	activePosition.value = null
	activeDimensions.value = null
	dragTarget.value = null
	resizeTarget.value = null
}

watch(
	() => activeElementId.value,
	() => {
		if (activeElementId.value == null) {
			removeDragAndResize()
			return
		}
		addDragAndResize()
	},
	{ immediate: true },
)

watch(
	() => presentation.data,
	() => {
		const currentSlide = presentation.data?.slides[slideIndex.value]
		if (!currentSlide) return
		slide.value.elements = JSON.parse(currentSlide.elements)
		slide.value.transition = currentSlide.transition
		slide.value.transitionDuration = currentSlide.transition_duration
	},
	{ immediate: true },
)

slideRect.value = useElementBounding(targetRef)
const scale = computed(() => {
	const matrix = transform.value.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

watch(
	() => activePosition.value,
	(position) => {
		if (!position) return
		const newleft = (position.left - slideRect.value.left) / scale.value
		const newTop = (position.top - slideRect.value.top) / scale.value
		activeElement.value = { ...activeElement.value, left: newleft, top: newTop }
	},
	{ immediate: true },
)

watch(
	() => activeDimensions.value,
	(dimensions) => {
		if (!dimensions) return
		if (activeElement.value && dimensions.width != activeElement.value.width) {
			const newWidth = dimensions.width / scale.value
			activeElement.value = { ...activeElement.value, width: newWidth }
		}
	},
	{ immediate: true },
)

const beforeSlideEnter = (el) => {
	if (!slide.value.transition) return
	if (slide.value.transition == 'Slide In') {
		transform.value = applyReverseTransition.value ? 'translateX(-100%)' : 'translateX(100%)'
		transition.value = 'none'
	} else if (slide.value.transition == 'Fade') {
		opacity.value = 0
	}
}

const slideEnter = (el, done) => {
	if (!slide.value.transition) return
	el.offsetWidth
	if (slide.value.transition == 'Slide In') {
		transition.value = `transform ${slide.value.transitionDuration}s ease-out`
		transform.value = 'translateX(0)'
	} else if (slide.value.transition == 'Fade') {
		transition.value = `opacity ${slide.value.transitionDuration}s`
		opacity.value = 1
	}
	done()
}

const beforeSlideLeave = (el) => {
	if (!slide.value.transition) return
	if (slide.value.transition == 'Slide In') {
		transition.value = 'none'
	} else if (slide.value.transition == 'Fade') {
		opacity.value = 1
	}
}

const slideLeave = (el, done) => {
	if (!slide.value.transition) return
	if (slide.value.transition == 'Slide In') {
		transform.value = applyReverseTransition.value ? 'translateX(100%)' : 'translateX(-100%)'
		transition.value = `transform ${slide.value.transitionDuration}s ease-out`
	} else if (slide.value.transition == 'Fade') {
		el.offsetWidth
		transition.value = `opacity ${slide.value.transitionDuration}s`
		opacity.value = 0
	}
	done()
}

defineExpose({
	targetRef,
})
</script>

<style src="../assets/styles/resizer.css"></style>
