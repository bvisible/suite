import { ref } from 'vue'
import { useEditor } from '@tiptap/vue-3'

import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import TextAlign from '@tiptap/extension-text-align'

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

export const useTextEditor = () => {
	const isEditorReady = ref(false)

	const editor = useEditor({
		extensions: [
			StarterKit,
			CustomTextStyle,
			TextAlign.configure({
				types: ['paragraph'],
			}),
		],
		editable: false,
		onCreate: () => {
			isEditorReady.value = true
		},
	})

	return {
		editor,
		isEditorReady,
	}
}
