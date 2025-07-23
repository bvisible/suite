import { Editor } from '@tiptap/vue-3'
import { Extension } from '@tiptap/core'

import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import Color from '@tiptap/extension-color'
import { Plugin } from 'prosemirror-state'

const CustomTextStyle = TextStyle.extend({
	addAttributes() {
		const attrs = {}

		const attributes = [
			'fontSize',
			'textTransform',
			'fontFamily',
			'lineHeight',
			'letterSpacing',
			'opacity',
		]

		const suffixes = {
			fontSize: 'px',
			letterSpacing: 'px',
			opacity: '%',
		}

		attributes.forEach((attr) => {
			attrs[attr] = {
				default: null,
				parseHTML: (element) => element.style[attr] || null,
				renderHTML: (attributes) => {
					if (!attributes[attr] && attr != 'opacity') return {}
					const attrName = attr.replace(/([A-Z])/g, '-$1').toLowerCase()
					return {
						style: `${attrName}: ${attributes[attr]}${suffixes[attr] || ''}`,
					}
				},
			}
		})

		return attrs
	},
})

const PastePlainText = Extension.create({
	name: 'pastePlainText',

	addProseMirrorPlugins() {
		const pasteWithInheritedStyles = (view, event) => {
			const plainText = event.clipboardData?.getData('text/plain')
			if (!plainText) return false

			const { state, dispatch } = view
			const { tr } = state

			dispatch(tr.insertText(plainText, state.selection.from, state.selection.to))
			return true
		}

		const pastePlugin = new Plugin({
			props: { handlePaste: pasteWithInheritedStyles },
		})

		return [pastePlugin]
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
			PastePlainText,
		],
		editable: false,
		content: content,
	})
}
