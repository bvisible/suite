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
				:key="activeSlideIndex"
			>
				<component
					ref="element"
					v-for="(element, index) in activeSlideElements"
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
		:class="activeSlideInFocus ? 'ring-[1px] ring-gray-200' : ''"
		@click="handleSlideClick"
	>
		<ElementAlignmentGuides
			v-if="activeElement && currentDataIndex != null && !isPanningOrZooming"
			:slideRect="slideRect"
		/>

		<div class="fixed -bottom-12 right-0 cursor-pointer p-3 flex items-center gap-4">
			<Trash size="14" :strokeWidth="1.5" class="text-gray-800" @click="deleteSlide" />
			<Copy size="14" :strokeWidth="1.5" class="text-gray-800" @click="duplicateSlide" />
			<SquarePlus
				size="14"
				:strokeWidth="1.5"
				class="text-gray-800"
				@click="insertSlide(activeSlideIndex)"
			/>
		</div>

		<component
			ref="element"
			v-for="(element, index) in activeSlideElements"
			:key="index"
			:is="SlideElement"
			:element="element"
			:data-index="index"
		/>
	</div>
</template>

<script setup>
import {
	onMounted,
	ref,
	useTemplateRef,
	watch,
	TransitionGroup,
	nextTick,
	computed,
	provide,
	onBeforeUnmount,
} from 'vue'
import { useElementBounding } from '@vueuse/core'

import SlideElement from '@/components/SlideElement.vue'
import ElementAlignmentGuides from '@/components/ElementAlignmentGuides.vue'

import { useDragAndDrop } from '@/utils/drag'
import { useResizer } from '@/utils/resizer'

import {
	presentation,
	activeSlideIndex,
	activeSlideInFocus,
	activeSlideElements,
	inSlideShow,
	position,
	dimensions,
	applyReverseTransition,
	slideTransition,
	slideTransitionDuration,
} from '@/stores/slide'
import { activeElement, currentDataIndex, currentFocusedIndex, resetFocus } from '@/stores/element'
import { insertSlide, deleteSlide, duplicateSlide } from '@/stores/slideActions'
import { Trash, Copy, SquarePlus } from 'lucide-vue-next'

const props = defineProps({
	slideCursor: String,
	isPanningOrZooming: Boolean,
})

const targetRef = useTemplateRef('target')

const { isDragging, dragTarget } = useDragAndDrop(position)
const { isResizing, resizeTarget, resizeMode } = useResizer(position, dimensions)

const transition = ref('none')
const transform = ref('none')
const opacity = ref(1)

const slideStyles = computed(() => {
	if (!presentation.data) return
	return {
		backgroundColor: presentation.data.slides[activeSlideIndex.value]?.background || 'white',
		cursor: inSlideShow.value ? props.slideCursor : isDragging.value ? 'move' : 'default',
		transition: transition.value,
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
	if (activeElement.value && currentFocusedIndex.value) {
		activeElement.content = document.querySelector(
			`[data-index="${currentFocusedIndex.value}"]`,
		).innerText
	}
	resetFocus()
	activeSlideInFocus.value = true
}

const handleSlideClick = (e) => {
	e.stopPropagation()
	if (e.target != targetRef.value) return
	if (inSlideShow.value) {
		activeSlideIndex.value += 1
		return
	} else selectSlide(e)
}

const addDragAndResize = () => {
	let el = document.querySelector(`[data-index="${currentDataIndex.value}"]`)
	if (!el || !activeElement.value) return
	dragTarget.value = el
	resizeTarget.value = el
	resizeMode.value = activeElement.value.type == 'text' ? 'width' : 'both'

	const elementRect = el.getBoundingClientRect()
	position.value = {
		top: elementRect.top,
		left: elementRect.left,
	}
}

const removeDragAndResize = () => {
	position.value = null
	dimensions.value = null
	dragTarget.value = null
	resizeTarget.value = null
}

watch(
	() => currentDataIndex.value,
	() => {
		if (currentDataIndex.value == null) {
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
		const currentSlide = presentation.data?.slides[activeSlideIndex.value]
		if (!currentSlide) return
		activeSlideElements.value = JSON.parse(currentSlide.elements)
		slideTransition.value = currentSlide.transition
		slideTransitionDuration.value = currentSlide.transition_duration
	},
	{ immediate: true },
)

const slideRect = useElementBounding(targetRef)

watch(
	() => position.value,
	() => {
		if (!position.value) return
		const currentScale = slideRect.width.value / 960
		const newleft = (position.value.left - slideRect.left.value) / currentScale
		const newTop = (position.value.top - slideRect.top.value) / currentScale
		activeElement.value = { ...activeElement.value, left: newleft, top: newTop }
	},
	{ immediate: true },
)

watch(
	() => dimensions.value,
	() => {
		if (!dimensions.value) return
		if (activeElement.value && dimensions.value.width != activeElement.value.width) {
			const currentScale = slideRect.width.value / 960
			const newWidth = dimensions.value.width / currentScale
			activeElement.value = { ...activeElement.value, width: newWidth }
		}
	},
	{ immediate: true },
)

const beforeSlideEnter = (el) => {
	if (!slideTransition.value) return
	if (slideTransition.value == 'Slide In') {
		transform.value = applyReverseTransition.value ? 'translateX(-100%)' : 'translateX(100%)'
		transition.value = 'none'
	} else if (slideTransition.value == 'Fade') {
		opacity.value = 0
	}
}

const slideEnter = (el, done) => {
	if (!slideTransition.value) return
	el.offsetWidth
	if (slideTransition.value == 'Slide In') {
		transition.value = `transform ${slideTransitionDuration.value}s ease-out`
		transform.value = 'translateX(0)'
	} else if (slideTransition.value == 'Fade') {
		transition.value = `opacity ${slideTransitionDuration.value}s`
		opacity.value = 1
	}
	done()
}

const beforeSlideLeave = (el) => {
	if (!slideTransition.value) return
	if (slideTransition.value == 'Slide In') {
		transition.value = 'none'
	} else if (slideTransition.value == 'Fade') {
		opacity.value = 1
	}
}

const slideLeave = (el, done) => {
	if (!slideTransition.value) return
	if (slideTransition.value == 'Slide In') {
		transform.value = applyReverseTransition.value ? 'translateX(100%)' : 'translateX(-100%)'
		transition.value = `transform ${slideTransitionDuration.value}s ease-out`
	} else if (slideTransition.value == 'Fade') {
		el.offsetWidth
		transition.value = `opacity ${slideTransitionDuration.value}s`
		opacity.value = 0
	}
	done()
}

defineExpose({
	targetRef,
})
</script>

<style src="../assets/styles/resizer.css"></style>
