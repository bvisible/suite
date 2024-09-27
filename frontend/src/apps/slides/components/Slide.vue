<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		class="slideContainer flex items-center justify-center"
		:class="inSlideShow ? 'bg-black-900' : ''"
		:style="{
			width: '800px',
			height: '450px',
		}"
	>
		<div
			ref="target"
			class="slide h-[450px] w-[800px] drop-shadow-xl"
			:style="{
				backgroundColor:
					(presentation.data &&
						presentation.data.slides[activeSlideIndex - 1].background) ||
					'white',
			}"
			:class="activeElement?.type == 'slide' ? 'ring-[1px] ring-gray-200' : ''"
			@click="selectSlide"
		>
			<div v-if="activeSlideElements">
				<component
					v-for="(element, index) in activeSlideElements"
					:key="index"
					:is="getDynamicComponent(element.type)"
					:element="element"
					@click="selectElement($event, element)"
					class="focus:outline-none focus:ring-[1.5px] focus:ring-blue-400"
					:class="isEqual(activeElement, element) ? 'ring-[1.5px] ring-blue-400' : ''"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref, unref, useTemplateRef, watch, onBeforeUnmount } from 'vue'
import { useDraggable, useElementBounding } from '@vueuse/core'

import TextElement from '@/components/TextElement.vue'
import ImageElement from '@/components/ImageElement.vue'

import {
	activeElement,
	activeSlideIndex,
	presentation,
	activeSlideElements,
	inSlideShow,
} from '@/stores/slide'
import { isEqual } from 'lodash'

const targetRef = useTemplateRef('target')

defineExpose({
	targetRef,
})

const selectSlide = (e) => {
	if (inSlideShow.value) return
	e.stopPropagation()
	if (e.target != targetRef.value) return
	activeElement.value = {
		type: 'slide',
	}
}

const selectElement = (e, element) => {
	if (inSlideShow.value) return
	e.stopPropagation()
	let el = e.target
	if (activeElement.value == element) return

	activeElement.value = element
	makeElementDraggable(el, element)
}

const { top: boundsTop, left: boundsLeft } = useElementBounding(targetRef)

const makeElementDraggable = (el, element) => {
	let initialX = el.getBoundingClientRect().left
	let initialY = el.getBoundingClientRect().top

	useDraggable(el, {
		initialValue: { x: initialX, y: initialY },
		onStart: ({ x, y }, e) => {
			if (element.isContentEditable || inSlideShow.value) return
			e.preventDefault()
			element.isDragging = true
		},
		onMove: ({ x, y }) => {
			if (element.isContentEditable || inSlideShow.value) return
			element.left = `${x - unref(boundsLeft)}px`
			element.top = `${y - unref(boundsTop)}px`
		},
		onEnd: ({ x, y }) => {
			if (element.isContentEditable || inSlideShow.value) return
			element.isDragging = false
			element.left = `${x - unref(boundsLeft)}px`
			element.top = `${y - unref(boundsTop)}px`
		},
	})
}

const handleKeyDown = (event) => {
	if (['Delete', 'Backspace'].includes(event.key) && !activeElement.value.isContentEditable) {
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
		if (!presentation.data) return
		if (old_val && presentation.data.slides[old_val - 1])
			presentation.data.slides[old_val - 1].elements = JSON.stringify(
				activeSlideElements.value,
			)
		if (presentation.data.slides[new_val - 1]) {
			if (presentation.data.slides[new_val - 1].elements)
				activeSlideElements.value = JSON.parse(
					presentation.data.slides[new_val - 1].elements,
				)
			else activeSlideElements.value = []
		}
	},
	{ immediate: true },
)

watch(
	() => presentation.data,
	() => {
		if (!presentation.data) return
		activeSlideElements.value = JSON.parse(
			presentation.data.slides[activeSlideIndex.value - 1].elements,
		)
	},
	{ immediate: true },
)

onMounted(() => {
	window.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	window.removeEventListener('keydown', handleKeyDown)
})

const getDynamicComponent = (type) => {
	switch (type) {
		case 'image':
			return ImageElement
		default:
			return TextElement
	}
}
</script>
