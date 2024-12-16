<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		ref="slideContainer"
		class="slideContainer flex items-center justify-center"
		:class="inSlideShow ? 'bg-black-900' : ''"
		:style="{
			width: '960px',
			height: '540px',
		}"
	>
		<div v-if="inSlideShow">
			<Transition @before-enter="beforeSlideEnter" @enter="slideEnter" @leave="slideLeave">
				<div
					ref="target"
					class="slide h-[540px] w-[960px] drop-shadow-xl"
					:style="slideStyles"
					v-if="currentTransitionSlide == activeSlideIndex"
					@click="handleSlideClick"
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
				v-if="activeElement && currentDataIndex != null"
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
	currentTransitionSlide,
	position,
	dimensions,
	applyReverseTransition,
	slideTransition,
	slideTransitionDuration,
} from '@/stores/slide'
import { activeElement, currentDataIndex, currentFocusedIndex, resetFocus } from '@/stores/element'
import { insertSlide, deleteSlide, duplicateSlide } from '@/stores/slideActions'
import { Trash, Copy, SquarePlus } from 'lucide-vue-next'

const zoom = defineModel('zoom')

const slideContainerRef = useTemplateRef('slideContainer')
const targetRef = useTemplateRef('target')

const { transform, transformOrigin, allowPanAndZoom } = zoom.value

const slideCursor = ref('auto')

const { isDragging, dragTarget } = useDragAndDrop(position)
const { isResizing, resizeTarget, resizeMode } = useResizer(position, dimensions)

const slideStyles = computed(() => {
	if (!presentation.data) return
	return {
		backgroundColor: presentation.data.slides[activeSlideIndex.value]?.background || 'white',
		transform: transform.value,
		transformOrigin: transformOrigin.value,
		cursor: inSlideShow.value ? slideCursor.value : isDragging.value ? 'move' : 'default',
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

const resetCursorVisibility = () => {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 3000)
}

const handleScreenChange = () => {
	inSlideShow.value = document.fullscreenElement

	if (document.fullscreenElement) {
		resetFocus()
		transformOrigin.value = ''
		allowPanAndZoom.value = false
		transform.value = 'scale(1.5, 1.5)'
		slideContainerRef.value.addEventListener('mousemove', resetCursorVisibility)
	} else {
		transform.value = ''
		transformOrigin.value = '0 0'
		allowPanAndZoom.value = true
		slideContainerRef.value.removeEventListener('mousemove', resetCursorVisibility)
	}
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
		let currentScale = slideRect.width.value / 960
		activeElement.value.left = (position.value.left - slideRect.left.value) / currentScale
		activeElement.value.top = (position.value.top - slideRect.top.value) / currentScale
	},
	{ immediate: true },
)

watch(
	() => dimensions.value,
	() => {
		if (!dimensions.value) return
		if (activeElement.value && dimensions.value.width != activeElement.value.width) {
			let currentScale = slideRect.width.value / 960
			activeElement.value.width = dimensions.value.width / currentScale
		}
	},
	{ immediate: true },
)

onMounted(() => {
	document.addEventListener('fullscreenchange', handleScreenChange)
})

onBeforeUnmount(() => {
	document.removeEventListener('fullscreenchange', handleScreenChange)
})

const beforeSlideEnter = (el) => {
	if (!slideTransition.value) return
	if (applyReverseTransition.value) el.style.transform = 'translateX(-100%) scale(1.5, 1.5)'
	else el.style.transform = 'translateX(100%) scale(1.5, 1.5)'
	el.style.transition = 'none'
}

const slideEnter = (el, done) => {
	if (!slideTransition.value) return
	el.offsetWidth
	el.style.transition = `transform ${slideTransitionDuration.value}s ease-out`
	el.style.transform = 'translateX(0) scale(1.5, 1.5)'
	done()
}

const slideLeave = (el, done) => {
	if (!slideTransition.value) return
	if (applyReverseTransition.value) el.style.transform = 'translateX(100%) scale(1.5, 1.5)'
	else el.style.transform = 'translateX(-100%) scale(1.5, 1.5)'
	el.style.transition = `transform ${slideTransitionDuration.value}s ease-out`
	done()
}

defineExpose({
	targetRef,
})
</script>

<style src="../assets/styles/resizer.css"></style>
