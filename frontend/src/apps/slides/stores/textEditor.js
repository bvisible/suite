import { ref, onMounted, onUnmounted } from 'vue'

import { Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'

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
			textTransform: {
				default: null,
				parseHTML: (el) => el.style.textTransform || null,
				renderHTML: (attrs) =>
					attrs.textTransform ? { style: `text-transform: ${attrs.textTransform}` } : {},
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

export const initTextEditor = (content) => {
	return new Editor({
		extensions: [
			StarterKit,
			CustomTextStyle,
			Underline,
			TextAlign.configure({
				types: ['paragraph'],
			}),
		],
		editable: false,
		content: content,
	})
}

export const activeEditor = ref(null)

export const toggleTextProperty = (property) => {
	const editor = activeEditor.value

	if (!editor) return

	switch (property) {
		case 'bold':
			editor.chain().focus().selectAll().toggleBold().run()
			break
		case 'italic':
			editor.chain().focus().selectAll().toggleItalic().run()
			break
		case 'strike':
			editor.chain().focus().selectAll().toggleStrike().run()
			break
		case 'uppercase':
			editor
				.chain()
				.focus()
				.setMark('textStyle', {
					textTransform:
						editor.getAttributes('textStyle').textTransform == 'uppercase'
							? null
							: 'uppercase',
				})
				.run()
			break
		default:
			editor.chain().focus().selectAll().toggleUnderline().run()
			break
	}
}

export const updateProperty = (property, value) => {
	const editor = activeEditor.value
	if (!editor) return

	switch (property) {
		case 'textAlign':
			editor.chain().focus().setTextAlign(value).run()
			break
	}
}

export function useTextStyles(editor) {
	const styles = ref({
		bold: false,
		italic: false,
		strike: false,
		underline: false,
		uppercase: false,
		textAlign: 'left',
	})

	const update = () => {
		if (!editor.value) return

		const attrs = editor.value.getAttributes('textStyle')

		styles.value = {
			bold: editor.value.isActive('bold'),
			italic: editor.value.isActive('italic'),
			strike: editor.value.isActive('strike'),
			underline: editor.value.isActive('underline'),
			uppercase: attrs.textTransform == 'uppercase',
			textAlign: editor.value.getAttributes('paragraph').textAlign || 'left',
		}
	}

	onMounted(() => {
		if (!editor.value) return
		editor.value.on('selectionUpdate', update)
		editor.value.on('transaction', update)
		update()
	})

	onUnmounted(() => {
		if (!editor.value) return
		editor.value.off('selectionUpdate', update)
		editor.value.off('transaction', update)
	})

	return {
		styles,
	}
}
