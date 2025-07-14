import { ref, onMounted, onUnmounted } from 'vue'

import { Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Color from '@tiptap/extension-color'

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
			lineHeight: {
				default: null,
				parseHTML: (element) => element.style.lineHeight || null,
				renderHTML: (attributes) => {
					if (!attributes.lineHeight) return {}
					return {
						style: `line-height: ${attributes.lineHeight}`,
					}
				},
			},
			letterSpacing: {
				default: null,
				parseHTML: (element) => element.style.letterSpacing || null,
				renderHTML: (attributes) => {
					if (!attributes.letterSpacing) return {}
					return {
						style: `letter-spacing: ${attributes.letterSpacing}px`,
					}
				},
			},
			opacity: {
				default: null,
				parseHTML: (element) => element.style.opacity || null,
				renderHTML: (attributes) => {
					return {
						style: `opacity: ${attributes.opacity}%`,
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
			Color,
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
		case 'fontSize':
			editor
				.chain()
				.focus()
				.selectAll()
				.setMark('textStyle', {
					fontSize: value ? `${value}px` : null,
				})
				.run()
			break
		case 'fontFamily':
			editor
				.chain()
				.focus()
				.selectAll()
				.setMark('textStyle', {
					fontFamily: value ? value : null,
				})
				.run()
			break
		case 'color':
			editor.chain().focus().selectAll().setColor(value).run()
			break
		case 'lineHeight':
			editor
				.chain()
				.focus()
				.selectAll()
				.setMark('textStyle', {
					lineHeight: value,
				})
				.run()
			break
		case 'letterSpacing':
			editor
				.chain()
				.focus()
				.selectAll()
				.setMark('textStyle', {
					letterSpacing: value,
				})
				.run()
			break
		case 'opacity':
			editor
				.chain()
				.focus()
				.selectAll()
				.setMark('textStyle', {
					opacity: value,
				})
				.run()
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
		fontSize: null,
		fontFamily: null,
		color: null,
		lineHeight: null,
		letterSpacing: null,
		opacity: null,
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
			fontSize: parseInt(attrs.fontSize, 10) || null,
			fontFamily: attrs.fontFamily || null,
			color: attrs.color || null,
			lineHeight: attrs.lineHeight,
			letterSpacing: parseInt(attrs.letterSpacing, 10),
			opacity: parseInt(attrs.opacity, 10),
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
