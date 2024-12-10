<template>
	<div
		class="focus:outline-none"
		:contenteditable="currentFocusedIndex == $attrs['data-index']"
		:style="textStyle"
		@click="selectElement"
	>
		{{ element.content }}
	</div>
</template>

<script setup>
import { ref, computed, inject, useAttrs } from 'vue'
import {
	activeElement,
	inSlideShow,
	currentDataIndex,
	currentFocusedIndex,
	setActiveElement,
} from '@/stores/slide'
import { handleSingleAndDoubleClick } from '@/utils/clickHandler'

const attrs = useAttrs()

const removeDragAndResize = inject('removeDragAndResize')

const element = defineModel('element', {
	type: Object,
	default: null,
})

const textStyle = computed(() => ({
	content: element.value.content,
	fontFamily: element.value.fontFamily,
	fontSize: `${element.value.fontSize}px`,
	fontWeight: element.value.fontWeight,
	fontStyle: element.value.fontStyle,
	textDecoration: element.value.textDecoration,
	textTransform: element.value.textTransform,
	userSelect: currentFocusedIndex.value == attrs['data-index'] ? 'text' : 'none',
	opacity: element.value.opacity / 100,
	lineHeight: element.value.lineHeight,
	letterSpacing: `${element.value.letterSpacing}px`,
	wordWrap: 'break-word',
	textAlign: element.value.textAlign,
	color: element.value.color,
	cursor: currentFocusedIndex.value == attrs['data-index'] ? 'text' : '',
}))

const selectElement = (e) => {
	if (inSlideShow.value) return
	handleSingleAndDoubleClick(e, setActiveText, setFocusElement)
}

const setActiveText = (e) => {
	e.stopPropagation()
	if (currentFocusedIndex.value == attrs['data-index']) return
	setActiveElement(element.value)
}

const setFocusElement = (e) => {
	e.stopPropagation()
	if (currentFocusedIndex.value == attrs['data-index']) return
	setActiveElement(element.value, true)
	removeDragAndResize()
}
</script>
