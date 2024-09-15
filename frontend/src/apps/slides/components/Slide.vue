<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		ref="target"
		class="slide h-[450px] w-[800px] bg-white drop-shadow-lg"
		:class="activeElement?.type == 'slide' ? 'ring-[1.5px] ring-[#808080]/50' : ''"
		v-if="slideElements"
		@click="selectSlide"
	>
		<component
			v-for="(element, index) in slideElements"
			:key="index"
			:is="TextElement"
			:element="element"
			@click="handleSingleAndDoubleClick($event, selectElement, makeElementEditable, element)"
			@blur="handleBlur($event, element)"
			class="focus:outline-none focus:ring-[1.5px] focus:ring-[#808080]/50"
			:class="activeElement == element ? 'ring-[1.5px] ring-[#808080]/50' : ''"
		/>
	</div>
</template>

<script setup>
import { ref, unref, useTemplateRef } from 'vue'
import { useDraggable, useElementBounding } from '@vueuse/core'

import TextElement from '@/components/TextElement.vue'
import { handleSingleAndDoubleClick } from '@/utils/clickHandler'

import { activeElement } from '@/stores/slide'

const targetRef = useTemplateRef('target')

defineExpose({
	targetRef,
})

defineProps({
	slideElements: Array,
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

const makeElementEditable = (e, element) => {
	e.stopPropagation()
	element.isContentEditable = true
}

const handleBlur = (e, element) => {
	element.isContentEditable = false
}
</script>
