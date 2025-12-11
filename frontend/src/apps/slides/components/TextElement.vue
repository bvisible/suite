<template>
	<EditorContent
		v-if="showEditor"
		:editor="activeEditor"
		:style="editorStyles"
		class="textElement"
		:class="isAutoWidth ? 'text-auto-width' : 'text-fixed-width'"
		@mousedown="handleMouseDown"
		@dblclick="handleDoubleClick"
	/>
	<div
		v-else-if="!inSlideShow"
		v-html="element.content"
		class="textElement select-none"
		:class="isAutoWidth ? 'text-auto-width' : 'text-fixed-width'"
		:style="element.editorMetadata"
		@dblclick="handleDoubleClick"
	></div>
	<SlideshowText
		v-else
		:content="element.content"
		class="textElement select-none"
		:class="isAutoWidth ? 'text-auto-width' : 'text-fixed-width'"
		:style="element.editorMetadata"
	/>
</template>

<script setup>
import { computed, onBeforeMount } from 'vue'

import SlideshowText from '@/components/SlideshowText.vue'

import { EditorContent, generateHTML } from '@tiptap/vue-3'

import { useTextEditor } from '@/composables/useTextEditor'

import { inSlideShow, readonlyMode } from '@/stores/presentation'
import { focusElementId, activeElement, activeElementIds, setEditableState } from '@/stores/element'
import { extensions } from '@/stores/tiptapSetup'

const { activeEditor, baseFontSize } = useTextEditor()

const props = defineProps({
	mode: {
		type: String,
		default: 'editor',
	},
})

const showEditor = computed(() => {
	if (!activeElement.value) return false
	return activeElement.value.id == element.value.id && props.mode == 'editor'
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const emit = defineEmits(['clearTimeouts'])

const isEditable = computed(() => focusElementId.value == element.value.id)

const editorStyles = computed(() => ({
	cursor: isEditable.value ? 'text' : '',
	userSelect: isEditable.value ? 'text' : 'none',
}))

const handleMouseDown = (e) => {
	if (!isEditable.value || readonlyMode.value) return

	e.stopPropagation()
}

const handleDoubleClick = (e) => {
	if (inSlideShow.value || isEditable.value || readonlyMode.value) {
		e.stopPropagation()
		return
	}

	emit('clearTimeouts')

	activeElementIds.value = [element.value.id]
	focusElementId.value = element.value.id

	if (activeElement.value.id == element.value.id && activeEditor.value) {
		setEditableState()
	}
}

const normalizeContent = () => {
	const content = element.value.content
	if (content && typeof content == 'object') {
		element.value.content = generateHTML(content, extensions)
	}
}

const isAutoWidth = computed(() => {
	return !element.value.width || element.value.width == 'auto'
})

onBeforeMount(() => normalizeContent())
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
	padding-left: 0.8em;
}

.tiptap > ul li::before,
.textElement > ul li::before {
	content: '\2022';
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

.text-auto-width,
.text-auto-width .ProseMirror {
	white-space: pre;
}

.text-fixed-width,
.text-fixed-width .ProseMirror {
	width: 100%;
	white-space: pre-wrap;
	overflow-wrap: break-word;
	hyphens: auto;
}
</style>
