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
						style: `font-size: ${attributes.fontSize}px`,
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
