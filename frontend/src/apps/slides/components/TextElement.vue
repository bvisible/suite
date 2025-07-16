<template>
	<EditorContent
		:editor="editor"
		:style="editorStyles"
		@mousedown="handleMouseDown"
		@dblclick="handleDoubleClick"
	/>
</template>

<script setup>
import { computed, watch } from 'vue'

import { EditorContent } from '@tiptap/vue-3'

import { useTextEditor } from '@/composables/useTextEditor'

import { focusElementId, deleteElements, activeElement, activeElementIds } from '@/stores/element'
import { initTextEditor } from '@/stores/tiptapSetup'

import { setCursorPositionAtEnd } from '@/utils/helpers'

const { activeEditor } = useTextEditor()

const element = defineModel('element', {
	type: Object,
	default: null,
})

const emit = defineEmits(['clearTimeouts'])

const editor = initTextEditor(element.value.content)

const editorStyles = computed(() => ({
	cursor: focusElementId.value == element.value.id ? 'text' : '',
}))

const handleMouseDown = (e) => {
	if (focusElementId.value == element.value.id) {
		e.stopPropagation()
		return
	}
}

const makeElementEditable = () => {
	emit('clearTimeouts')

	activeEditor.value = editor
	focusElementId.value = element.value.id
	activeElementIds.value = []

	activeEditor.value.setEditable(true)
	activeEditor.value.commands.focus('end')
}

const handleDoubleClick = (e) => {
	if (focusElementId.value == element.value.id) {
		e.stopPropagation()
		return
	}

	makeElementEditable()
}

const isEditorEmpty = () => {
	const json = activeEditor.value.getJSON()

	if (!json || !json.content) return true

	if (
		json.content.length == 1 &&
		json.content[0].type == 'paragraph' &&
		(!json.content[0].content || json.content[0].content.length == 0)
	) {
		return true
	}

	return false
}

const blurAndSaveContent = async (id) => {
	activeEditor.value.setEditable(false)
	activeEditor.value.commands.blur()

	if (isEditorEmpty()) {
		deleteElements(null, [id])
	} else {
		element.value.content = editor.getJSON()
	}
}

watch(
	() => activeElement.value,
	(el, oldEl) => {
		if (oldEl?.type == 'text' && oldEl.id == element.value.id) {
			blurAndSaveContent(oldEl.id)
		}
		if (el?.type == 'text' && el.id == element.value.id) {
			activeEditor.value = editor
		}
	},
)
</script>
