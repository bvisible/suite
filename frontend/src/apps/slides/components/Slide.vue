<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		ref="slideContainer"
		class="slideContainer flex items-center justify-center"
		:class="inSlideShow ? 'bg-black-900' : ''"
		:style="{
			width: '960px',
			height: '540px',
			cursor: inSlideShow ? slideCursor : 'default',
		}"
	>
		<div
			ref="target"
			class="slide h-[540px] w-[960px] drop-shadow-xl"
			:style="slideStyles"
			:class="activeElement?.type == 'slide' ? 'ring-[1px] ring-gray-200' : ''"
			@click="handleSlideClick"
		>
			<ElementAlignmentGuides v-if="activeElement" :slideRect="slideRect" />

			<div v-if="activeSlideElements">
				<TransitionGroup
					v-if="inSlideShow"
					tag="div"
					@enter="handleSlideEnter"
					@leave="handleSlideLeave"
				>
					<component
						v-for="(element, index) in activeSlideElements"
						:key="index"
						:is="SlideElement"
						:element="element"
					/>
				</TransitionGroup>
				<component
					v-else
					ref="element"
					v-for="(element, index) in activeSlideElements"
					:key="index"
					:is="SlideElement"
					:element="element"
					:data-index="index"
				/>
			</div>
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
	currentDataIndex,
	activeElement,
	focusedElement,
	activeSlideIndex,
	presentation,
	activeSlideElements,
	inSlideShow,
	position,
	dimensions,
	currentPairedDataIndex,
} from '@/stores/slide'

const zoom = defineModel('zoom')
const emit = defineEmits(['changeSlide'])

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
	}
})

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	if (isResizing.value) {
		isResizing.value = false
		return
	}
	activeElement.value = {
		type: 'slide',
	}
	if (focusedElement.value) {
		focusedElement.value.content = document.querySelector(
			`[data-index="${currentDataIndex.value}"]`,
		).innerText
		focusedElement.value = null
	}
	currentDataIndex.value = null
	currentPairedDataIndex.value = null
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

const duplicateElement = (e) => {
	e.preventDefault()
	if (activeElement.value) {
		let newElement = JSON.parse(JSON.stringify(activeElement.value))
		newElement.top += 10
		newElement.left += 10
		activeSlideElements.value.push(newElement)
		activeElement.value = newElement
		currentDataIndex.value = activeSlideElements.value.indexOf(newElement)
	}
}

const deleteElement = (e) => {
	if (!activeElement.value && !focusedElement.value) return
	activeSlideElements.value.splice(currentDataIndex.value, 1)
	selectSlide(e)
}

const handleKeyDown = (event) => {
	if (document.activeElement.tagName == 'INPUT') return
	if (['Delete', 'Backspace'].includes(event.key)) deleteElement(event)
	else if (event.key == 'd' && event.metaKey) duplicateElement(event)
	else if (event.key == 'ArrowUp') {
		if (activeElement.value && activeElement.value.type != 'slide')
			position.value = { ...position.value, top: position.value.top - 1 }
		else emit('changeSlide', activeSlideIndex.value - 1)
	} else if (event.key == 'ArrowDown') {
		if (activeElement.value && activeElement.value.type != 'slide')
			position.value = { ...position.value, top: position.value.top + 1 }
		else emit('changeSlide', activeSlideIndex.value + 1)
	} else if (event.key == 'ArrowLeft') {
		if (activeElement.value)
			position.value = { ...position.value, left: position.value.left - 1 }
	} else if (event.key == 'ArrowRight') {
		if (activeElement.value)
			position.value = { ...position.value, left: position.value.left + 1 }
	}
}

const handleSlideEnter = (el, done) => {
	el.style.opacity = 0
	nextTick(() => {
		el.style.transition = 'opacity 1s'
		el.style.opacity = 1
	})
}

const handleSlideLeave = (el, done) => {
	el.style.opacity = 1
	nextTick(() => {
		el.style.transition = 'opacity 1s'
		el.style.opacity = 0
	})
}

function resetCursorVisibility() {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 2000)
}

const handleScreenChange = () => {
	inSlideShow.value = document.fullscreenElement

	if (document.fullscreenElement) {
		activeElement.value = null
		transformOrigin.value = ''
		transform.value = 'scale(1.5, 1.5)'
		allowPanAndZoom.value = false
		targetRef.value.addEventListener('mousemove', resetCursorVisibility)
	} else {
		transform.value = ''
		transformOrigin.value = '0 0'
		allowPanAndZoom.value = true
		targetRef.value.removeEventListener('mousemove', resetCursorVisibility)
	}
}

watch(
	() => activeElement.value,
	() => {
		removeDragAndResize()
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

defineExpose({
	targetRef,
})

provide('removeDragAndResize', removeDragAndResize)
provide('isDragging', isDragging)
</script>

<style src="../assets/styles/resizer.css"></style>
