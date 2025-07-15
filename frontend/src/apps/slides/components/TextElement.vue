<template>
	<EditorContent
		:editor="editor"
		:style="editorStyles"
		@mousedown="handleMouseDown"
		@dblclick="handleDoubleClick"
	/>
</template>

<script setup>
import { computed, watch, onMounted } from 'vue'

import { focusElementId, deleteElements, activeElement, activeElementIds } from '@/stores/element'
import { setCursorPositionAtEnd } from '@/utils/helpers'

import { EditorContent } from '@tiptap/vue-3'

import { useTextEditor } from '@/composables/useTextEditor'
import { initTextEditor } from '@/stores/tiptapSetup'
import { updateSelectionBounds } from '@/stores/slide'

const { activeEditor } = useTextEditor()

const element = defineModel('element', {
	type: Object,
	default: null,
})

const emit = defineEmits(['clearTimeouts'])

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

const handleMouseDown = (e) => {
	if (focusElementId.value == element.value.id) {
		e.stopPropagation()
		return
	}
}

const handleDoubleClick = (e) => {
	if (focusElementId.value == element.value.id) {
		e.stopPropagation()
		return
	}

	emit('clearTimeouts')

	activeEditor.value = editor
	focusElementId.value = element.value.id
	activeElementIds.value = []

	activeEditor.value.setEditable(true)
	activeEditor.value.commands.focus('end')
}

watch(
	() => activeElement.value,
	(el, oldEl) => {
		if (oldEl?.type == 'text' && oldEl.id == element.value.id) {
			activeEditor.value.setEditable(false)
			activeEditor.value.commands.blur()
			element.value.content = editor.getJSON()
		}
		if (el?.type == 'text' && el.id == element.value.id) {
			activeEditor.value = editor
		}
	},
	{ immediate: true },
)
</script>
