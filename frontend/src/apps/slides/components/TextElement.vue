<template>
	<EditorContent
		v-if="activeElement?.id == element.id"
		:editor="activeEditor"
		:style="editorStyles"
		@mousedown="handleMouseDown"
		@dblclick="handleDoubleClick"
	/>
	<div
		v-else
		v-html="element.content"
		class="textElement"
		:style="element.editorMetadata"
		@dblclick="handleDoubleClick"
	></div>
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

const isEditable = computed(() => focusElementId.value == element.value.id)

const editorStyles = computed(() => ({
	cursor: isEditable.value ? 'text' : 'default',
	userSelect: isEditable.value ? 'text' : 'none',
}))

const handleMouseDown = (e) => {
	if (isEditable.value) {
		e.stopPropagation()
		return
	}
}

const makeElementEditable = () => {
	emit('clearTimeouts')

	activeElementIds.value = []

	activeEditor.value.setEditable(true)
	activeEditor.value.commands.focus()
	activeEditor.value.commands.setTextSelection({
		from: 0,
		to: activeEditor.value.state.doc.content.size,
	})
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

const blurAndSaveContent = (id) => {
	activeEditor.value.setEditable(false)
	activeEditor.value.commands.blur()

	if (isEditorEmpty()) {
		deleteElements(null, [id])
	} else {
		element.value.content = activeEditor.value.getHTML()
		element.value.editorMetadata = {
			lineHeight: parseFloat(activeEditor.value.view.dom.style['line-height']),
		}
	}
}

watch(
	() => focusElementId.value,
	(newId, oldId) => {
		if (newId == element.value.id) {
			makeElementEditable()
		}
	},
)

watch(
	() => activeElement.value,
	(newVal, oldVal) => {
		if (oldVal?.type == 'text') {
			blurAndSaveContent(oldVal.id)
		}
		if (newVal?.type == 'text') {
			initTextEditor(newVal.id, newVal.content, newVal.editorMetadata)
		}
	},
)
</script>

<style>
.ProseMirror {
	caret-color: currentColor;
}

.tiptap ul,
.textElement > ul {
	list-style: none;
	padding-left: 0;
}

.tiptap > ul li,
.textElement > ul li {
	position: relative;
	padding-left: 0.6em;
}

.tiptap > ul li::before,
.textElement > ul li::before {
	content: '•';
	position: absolute;
	left: 0;
	top: 0;
	font-size: 1em;
}

.tiptap ol,
.textElement ol {
	list-style: none;
	margin: 0;
	padding: 0;
	counter-reset: step;
}

.tiptap ol li,
.textElement ol li {
	counter-increment: step;
	position: relative;
	padding-left: calc(2ch + 0.2em);
}

.tiptap ol li::before,
.textElement ol li::before {
	content: counter(step) '.';
	position: absolute;
	left: 0;
	top: 0;
	width: 2ch;
	text-align: right;
}
</style>
