<template>
	<!-- <div
		class="focus:outline-none"
		:contenteditable="focusElementId == element.id"
		:style="textStyle"
		@focus="setCursorPositionAtEnd"
		@blur="handleBlur"
	>
		{{ element.content }}
	</div> -->

	<EditorContent :editor="editor" class="p-0" />
</template>

<script setup>
import { computed } from 'vue'

import { focusElementId, deleteElements } from '@/stores/element'
import { setCursorPositionAtEnd } from '@/utils/helpers'

import { EditorContent, useEditor } from '@tiptap/vue-3'
import { StarterKit } from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import TextAlign from '@tiptap/extension-text-align'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const CustomTextStyle = TextStyle.extend({
	addAttributes() {
		return {
			fontSize: {
				default: null,
				parseHTML: (element) => element.style.fontSize || null,
				renderHTML: (attributes) => {
					if (!attributes.fontSize) return {}
					return {
						style: `font-size: ${attributes.fontSize}`,
					}
				},
			},
			fontFamily: {
				default: null,
				parseHTML: (element) => element.style.fontFamily || null,
				renderHTML: (attributes) => {
					if (!attributes.fontFamily) return {}
					return {
						style: `font-family: ${attributes.fontFamily}`,
					}
				},
			},
		}
	},
})

const editor = useEditor({
	extensions: [
		StarterKit,
		CustomTextStyle,
		TextAlign.configure({
			types: ['paragraph'],
		}),
	],
	content: element.value.content || '',
	editable: false,
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

const editorStyles = computed(() => ({
	cursor: focusElementId.value == element.value.id ? 'text' : '',
}))

const handleBlur = (e) => {
	if (element.value.content.trim() === '') {
		deleteElements()
	}
	element.value.content = e.target.innerText
}
</script>
