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

import { inSlideShow } from '@/stores/presentation'
import { focusElementId, deleteElements, activeElement, activeElementIds } from '@/stores/element'

const { activeEditor, initTextEditor } = useTextEditor()

const element = defineModel('element', {
	type: Object,
	default: null,
})

const emit = defineEmits(['clearTimeouts'])

const editor = initTextEditor(element.value.content, element.value.editorMetadata)

const isEditable = computed(() => focusElementId.value == element.value.id)

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
	activeElementIds.value = []

	activeEditor.value.setEditable(true)
	activeEditor.value.commands.focus()
	activeEditor.value.commands.selectAll()
}

const handleDoubleClick = (e) => {
	if (inSlideShow.value || isEditable.value) {
		e.stopPropagation()
		return
	}

	focusElementId.value = element.value.id
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
	() => focusElementId.value,
	(newId, oldId) => {
		if (oldId && oldId != newId) {
			blurAndSaveContent(oldId)
		}
		if (newId == element.value.id) {
			makeElementEditable()
		}
	},
)

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

<style>
.tiptap > ul {
	list-style: none;
	padding-left: 0;
}

.tiptap > ul li {
	position: relative;
	padding-left: 0.6em;
}

.tiptap > ul li::before {
	content: '•';
	position: absolute;
	left: 0;
	top: 0.1em;
	font-size: 1em;
}

.tiptap ol {
	list-style: none;
	margin: 0;
	padding: 0;
	counter-reset: step;
}

.tiptap ol li {
	counter-increment: step;
	position: relative;
	padding-left: calc(2ch + 0.2em);
}

.tiptap ol li::before {
	content: counter(step) '.';
	position: absolute;
	left: 0;
	top: 0;
	width: 2ch;
	text-align: right;
}
</style>
