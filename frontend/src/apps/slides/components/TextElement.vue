<template>
	<EditorContent :editor="editor" class="p-0" />
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'

import { focusElementId, deleteElements, activeElement } from '@/stores/element'
import { setCursorPositionAtEnd } from '@/utils/helpers'

import { EditorContent } from '@tiptap/vue-3'

import { initTextEditor, activeEditor } from '@/stores/textEditor'
import { updateSelectionBounds } from '@/stores/slide'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const editor = initTextEditor(element.value.content)

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

const editorStyles = computed(() => ({
	cursor: focusElementId.value == element.value.id ? 'text' : '',
}))

const handleBlur = (e) => {
	if (element.value.content.trim() === '') {
		deleteElements()
	}
	element.value.content = e.target.innerText
}

watch(
	() => activeElement.value,
	(el) => {
		if (el?.type === 'text' && el.id == element.value.id) {
			activeEditor.value = editor
		}
	},
	{ immediate: true },
)
</script>
