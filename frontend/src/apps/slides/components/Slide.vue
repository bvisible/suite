<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		ref="target"
		class="slide h-[450px] w-[800px] bg-white drop-shadow-lg"
		:class="activeElement?.type == 'slide' ? 'ring-[1px] ring-gray-200' : ''"
		v-if="activeSlideElements"
		@click="selectSlide"
	>
		<component
			v-for="(element, index) in activeSlideElements"
			:key="index"
			:is="TextElement"
			:element="element"
			@click="selectElement($event, element)"
			class="focus:outline-none focus:ring-[1.5px] focus:ring-[#808080]/50"
			:class="isEqual(activeElement, element) ? 'ring-[1.5px] ring-[#808080]/50' : ''"
		/>
	</div>
</template>

<script setup>
import { onMounted, ref, unref, useTemplateRef, watch, onBeforeUnmount } from 'vue'
import { useDraggable, useElementBounding } from '@vueuse/core'

import TextElement from '@/components/TextElement.vue'

import {
	activeElement,
	activeSlide,
	activeSlideIndex,
	presentation,
	activeSlideElements,
} from '@/stores/slide'
import { isEqual } from 'lodash'

const targetRef = useTemplateRef('target')

defineExpose({
	targetRef,
})

const selectSlide = (e) => {
	e.stopPropagation()
	if (e.target != targetRef.value) return
	activeElement.value = {
		type: 'slide',
	}
}

const selectElement = (e, element) => {
	e.stopPropagation()
	let el = e.target
	if (activeElement.value == element) return

	if (el.classList.contains('textElement')) {
		activeElement.value = element
		makeElementDraggable(el, element)
	}
}

const { top: boundsTop, left: boundsLeft } = useElementBounding(targetRef)

const makeElementDraggable = (el, element) => {
	let initialX = el.getBoundingClientRect().left
	let initialY = el.getBoundingClientRect().top

	useDraggable(el, {
		initialValue: { x: initialX, y: initialY },
		onStart: ({ x, y }, e) => {
			if (element.isContentEditable) return
			e.preventDefault()
			element.isDragging = true
		},
		onMove: ({ x, y }) => {
			if (element.isContentEditable) return
			element.left = `${x - unref(boundsLeft)}px`
			element.top = `${y - unref(boundsTop)}px`
		},
		onEnd: ({ x, y }) => {
			if (element.isContentEditable) return
			element.isDragging = false
			element.left = `${x - unref(boundsLeft)}px`
			element.top = `${y - unref(boundsTop)}px`
		},
	})
}

const handleKeyDown = (event) => {
	if (['Delete', 'Backspace'].includes(event.key)) {
		if (activeElement.value) {
			activeSlideElements.value = activeSlideElements.value.filter(
				(el) => !isEqual(el, activeElement.value),
			)
			activeElement.value = null
		}
	}
}

watch(
	() => activeSlideIndex.value,
	(new_val, old_val) => {
		if (old_val)
			presentation.data.slides[old_val - 1].elements = JSON.stringify(
				activeSlideElements.value,
			)
		if (!activeSlide.value.elements) activeSlideElements.value = []
		else activeSlideElements.value = JSON.parse(activeSlide.value.elements)
	},
	{ immediate: true },
)

onMounted(() => {
	window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	window.removeEventListener('keydown', handleKeyDown)
})
</script>
