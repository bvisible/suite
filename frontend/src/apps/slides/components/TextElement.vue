<template>
	<div
		class="focus:outline-none"
		:contenteditable="focusElementId == element.id"
		:style="textStyle"
		@focus="setCursorPosition"
		@blur="handleBlur"
	>
		{{ element.content }}
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { focusElementId, deleteElements } from '@/stores/element'

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
	wordWrap: element.value.width == 'auto' ? 'normal' : 'break-word',
	textAlign: element.value.textAlign,
	color: element.value.color,
	cursor: focusElementId.value == element.value.id ? 'text' : '',
}))

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
	if (element.value.content.trim() === '') {
		deleteElements()
	}
	element.value.content = e.target.innerText
}
</script>
