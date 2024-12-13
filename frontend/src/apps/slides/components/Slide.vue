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
				<Trash size="14" strokeWidth="1.5" class="text-gray-800" @click="deleteSlide" />
				<Copy size="14" strokeWidth="1.5" class="text-gray-800" @click="duplicateSlide" />
				<SquarePlus
					size="14"
					strokeWidth="1.5"
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
} from '@/stores/slide'
import {
	activeElement,
	currentDataIndex,
	currentFocusedIndex,
	currentPairedDataIndex,
	resetFocus,
	addTextElement,
} from '@/stores/element'
import { changeSlide, insertSlide, deleteSlide, duplicateSlide } from '@/stores/slideActions'
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

const handleDuplicate = (e) => {
	e.preventDefault()
	if (activeElement.value) {
		let newElement = JSON.parse(JSON.stringify(activeElement.value))
		newElement.top += 40
		newElement.left += 40
		activeSlideElements.value.push(newElement)
		nextTick(() => (currentDataIndex.value = activeSlideElements.value.indexOf(newElement)))
	} else duplicateSlide()
}

const handleDelete = (e) => {
	if (currentFocusedIndex.value != null) return
	if (activeElement.value) {
		activeSlideElements.value.splice(currentDataIndex.value, 1)
		selectSlide(e)
	} else deleteSlide()
}

const handleKeyDown = (event) => {
	if (document.activeElement.tagName == 'INPUT') return
	if (['Delete', 'Backspace'].includes(event.key)) handleDelete(event)
	else if (event.key == 'd' && event.metaKey) handleDuplicate(event)
	else if (event.key == 'Escape') resetFocus()
	else if (event.key == 't') addTextElement()
	else if (event.key == 'ArrowUp') {
		if (activeElement.value) position.value = { ...position.value, top: position.value.top - 1 }
		else changeSlide(activeSlideIndex.value - 1)
	} else if (event.key == 'ArrowDown') {
		if (activeElement.value) position.value = { ...position.value, top: position.value.top + 1 }
		else changeSlide(activeSlideIndex.value + 1)
	} else if (event.key == 'ArrowLeft') {
		if (activeElement.value)
			position.value = { ...position.value, left: position.value.left - 1 }
	} else if (event.key == 'ArrowRight') {
		if (activeElement.value)
			position.value = { ...position.value, left: position.value.left + 1 }
	}
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
		if (!presentation.data?.slides[activeSlideIndex.value]?.elements) return
		activeSlideElements.value = JSON.parse(
			presentation.data.slides[activeSlideIndex.value].elements,
		)
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
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleScreenChange)
})

onBeforeUnmount(() => {
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleScreenChange)
})

const beforeSlideEnter = (el) => {
	if (applyReverseTransition.value) el.style.transform = 'translateX(-100%) scale(1.5, 1.5)'
	else el.style.transform = 'translateX(100%) scale(1.5, 1.5)'
	el.style.transition = 'none'
}

const slideEnter = (el, done) => {
	el.offsetWidth
	el.style.transition = 'transform 0.7s ease-out'
	el.style.transform = 'translateX(0) scale(1.5, 1.5)'
	done()
}

const slideLeave = (el, done) => {
	if (applyReverseTransition.value) el.style.transform = 'translateX(100%) scale(1.5, 1.5)'
	else el.style.transform = 'translateX(-100%) scale(1.5, 1.5)'
	el.style.transition = 'transform 0.7s ease-out'
	done()
}

defineExpose({
	targetRef,
})
</script>

<style src="../assets/styles/resizer.css"></style>
