<template>
	<div
		class="focus:outline-none"
		:contenteditable="focusElementId == element.id"
		:style="textStyle"
		@click="selectElement"
		@focus="setCursorPosition"
		@blur="handleBlur"
	>
		{{ element.content }}
	</div>
</template>

<script setup>
import { computed, nextTick } from 'vue'

import { inSlideShow } from '@/stores/presentation'
import { focusElementId, setActiveElements } from '@/stores/element'
import { handleSingleAndDoubleClick } from '@/utils/helpers'

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
	userSelect: focusElementId.value == element.value.id ? 'text' : 'none',
	opacity: element.value.opacity / 100,
	lineHeight: element.value.lineHeight,
	letterSpacing: `${element.value.letterSpacing}px`,
	wordWrap: 'break-word',
	textAlign: element.value.textAlign,
	color: element.value.color,
	cursor: focusElementId.value == element.value.id ? 'text' : '',
}))

const selectElement = (e) => {
	if (inSlideShow.value) return
	handleSingleAndDoubleClick(e, setActiveText, setFocusElement)
}

const setActiveText = (e) => {
	e.stopPropagation()
	if (focusElementId.value == element.value.id) return
	setActiveElements([element.value.id])
}

const setFocusElement = (e) => {
	e.stopPropagation()
	if (focusElementId.value == element.value.id) return
	setActiveElements([element.value.id], true)
	nextTick(() => {
		e.target.focus()
	})
}

const setCursorPosition = (e) => {
	const range = document.createRange()
	const selection = window.getSelection()

	range.selectNodeContents(e.target)
	// set cursor to end of text
	range.collapse(false)

	selection.removeAllRanges()
	selection.addRange(range)
}

const handleBlur = (e) => {
	element.value.content = e.target.innerText
}
</script>
