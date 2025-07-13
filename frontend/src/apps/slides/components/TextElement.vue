<template>
	<EditorContent :editor="editor" class="focus:outline-none" />
</template>

<script setup>
import { computed } from 'vue'

import { focusElementId, deleteElements } from '@/stores/element'
import { setCursorPositionAtEnd } from '@/utils/helpers'

import { EditorContent, useEditor } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const editor = useEditor({
	extensions: [StarterKit],
	content: element.value.content || '',
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
	whiteSpace: 'pre-wrap',
	wordWrap: element.value.width == 'auto' ? 'normal' : 'break-word',
	textAlign: element.value.textAlign,
	color: element.value.color,
	cursor: focusElementId.value == element.value.id ? 'text' : '',
}))

const handleBlur = (e) => {
	if (element.value.content.trim() === '') {
		deleteElements()
	}
	element.value.content = e.target.innerText
}
</script>
