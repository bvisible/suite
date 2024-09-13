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

const targetRef = useTemplateRef('target')

defineExpose({
	targetRef,
})

defineProps({
	slideElements: Array,
})

const activeElement = defineModel('activeElement', {
	type: Object,
	default: null,
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

const makeElementDraggable = (el, element) => {
	element.styles.cursor = 'grab'

	const { top: boundsTop, left: boundsLeft } = useElementBounding(targetRef)

	let initialX = el.getBoundingClientRect().left
	let initialY = el.getBoundingClientRect().top

	useDraggable(el, {
		initialValue: { x: initialX, y: initialY },
		onStart: ({ x, y }, e) => {
			if (element.isContentEditable) return
			e.preventDefault()
			element.styles.cursor = 'grabbing'
		},
		onMove: ({ x, y }) => {
			if (element.isContentEditable) return
			element.x = `${x - unref(boundsLeft)}px`
			element.y = `${y - unref(boundsTop)}px`
		},
		onEnd: ({ x, y }) => {
			if (element.isContentEditable) return
			element.styles.cursor = 'grab'
			element.x = `${x - unref(boundsLeft)}px`
			element.y = `${y - unref(boundsTop)}px`
		},
	})
}

const makeElementEditable = (e, element) => {
	e.stopPropagation()
	element.isContentEditable = true
	element.styles.userSelect = 'text'
	element.styles.cursor = 'text'
	e.target.focus()
}

const handleBlur = (e, element) => {
	element.isContentEditable = false
	element.styles.userSelect = 'none'
	element.styles.cursor = 'grab'
}
</script>
