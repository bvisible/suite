import { ref, reactive, watch } from 'vue'
import { Editor } from '@tiptap/vue-3'
import { extensions } from '@/stores/tiptapSetup'
import { TextSelection } from 'prosemirror-state'

const activeEditor = ref(null)

const editorStyles = reactive({
	textAlign: 'left',
	bold: false,
	italic: false,
	strike: false,
	underline: false,
	uppercase: false,
	fontSize: null,
	fontFamily: null,
	color: null,
	lineHeight: null,
	letterSpacing: null,
	opacity: null,
	bulletList: false,
	orderedList: false,
})

export const useTextEditor = () => {
	const setEditorStyles = (editor) => {
		if (!editor) return

		const activeStyles = editor.getAttributes('textStyle')

		Object.assign(editorStyles, {
			textAlign: editor.getAttributes('paragraph').textAlign || 'left',
			bold: editor.isActive('bold'),
			italic: editor.isActive('italic'),
			strike: editor.isActive('strike'),
			underline: editor.isActive('underline'),
			bulletList: editor.isActive('bulletList'),
			orderedList: editor.isActive('orderedList'),
			uppercase: activeStyles.textTransform == 'uppercase',
			fontSize: parseInt(activeStyles.fontSize, 10) || null,
			fontFamily: activeStyles.fontFamily || null,
			color: activeStyles.color || null,
			lineHeight: activeStyles.lineHeight,
			letterSpacing: parseInt(activeStyles.letterSpacing, 10),
			opacity: parseInt(activeStyles.opacity, 10),
		})
	}

	const update = ({ transaction, editor }) => {
		setEditorStyles(editor)

		const changeListMarkers = !editor.isEditable || editor.state.selection.empty
		changeListMarkers && updateListStyles({ transaction, editor })
	}

	const updateListStyles = ({ transaction, editor }) => {
		if (!transaction.docChanged || transaction.getMeta('custom-list-style-applied')) return

		const styles = {
			fontSize: editorStyles.fontSize,
			fontFamily: editorStyles.fontFamily,
			color: editorStyles.color,
			opacity: editorStyles.opacity,
		}

		const { state } = editor
		const listItemType = state.schema.nodes.listItem
		const tr = state.tr

		if (!listItemType || !tr) return

		let hasChanged = false
		state.doc.descendants((node, pos) => {
			if (!node.type || node.type.name != 'listItem') return

			if (node.type == listItemType) {
				let currentStyle = typeof node.attrs.style == 'string' ? node.attrs.style : ''
				let newStyle = currentStyle

				Object.entries(styles).forEach(([property, value]) => {
					if (value == null) return
					newStyle = getCSSString(newStyle, property, value)
				})

				if (newStyle != currentStyle) {
					tr.setNodeMarkup(pos, listItemType, {
						...node.attrs,
						style: newStyle,
					})
					hasChanged = true
				}
			}
		})

		if (hasChanged) {
			tr.setMeta('custom-list-style-applied', true)
			editor.view.dispatch(tr)
		}
	}

	const markCommands = {
		bold: 'toggleBold',
		italic: 'toggleItalic',
		strike: 'toggleStrike',
		underline: 'toggleUnderline',
	}

	const toggleCapitalize = (chain) => {
		const val = activeEditor.value.getAttributes('textStyle').textTransform
		const newVal = val == 'uppercase' ? null : 'uppercase'

		chain
			.setMark('textStyle', {
				textTransform: newVal,
			})
			.run()
	}

	const toggleMark = (property) => {
		const currentEditor = activeEditor.value

		const chain = currentEditor.chain().focus()

		const { empty } = currentEditor.state.selection
		if (empty) chain.selectAll()

		if (property == 'uppercase') return toggleCapitalize(chain)

		chain[markCommands[property]](property).run()
	}

	const selectListBlock = () => {
		const { state } = activeEditor.value
		const doc = state.doc

		let selectionStart = null,
			selectionEnd = null

		doc.descendants((node, pos) => {
			if (!node.isTextblock) return

			selectionEnd = pos + node.nodeSize - 1

			if (!selectionStart) {
				selectionStart = pos + 1
			}
		})

		if (selectionStart && selectionEnd) {
			const selection = TextSelection.create(doc, selectionStart, selectionEnd)
			const transaction = state.tr.setSelection(selection)
			activeEditor.value.view.dispatch(transaction)
		}
	}

	const getCSSString = (currentStyle, property, value) => {
		const val =
			property == 'opacity' ? `${value}%` : property == 'fontSize' ? `${value}px` : value
		const prop = property.replace(/([A-Z])/g, '-$1').toLowerCase()
		const newStyle = `${prop}: ${val}`
		return currentStyle ? `${currentStyle}; ${newStyle}` : newStyle
	}

	const setListProperty = () => {
		if (!activeEditor.value.isEditable) selectListBlock()

		const chain = activeEditor.value.chain().focus()

		if (activeEditor.value.isActive('orderedList')) {
			chain.liftListItem('listItem').run()
		} else if (activeEditor.value.isActive('bulletList')) {
			chain.liftListItem('listItem').wrapInList('orderedList').run()
		} else {
			chain.wrapInList('bulletList').run()
		}
	}

	const updateProperty = (property, value) => {
		const currentEditor = activeEditor.value

		const chain = currentEditor.chain().focus()

		if (property == 'list') return setListProperty()

		const { empty } = currentEditor.state.selection
		if (empty) chain.selectAll()

		switch (property) {
			case 'textAlign':
				chain.setTextAlign(value).run()
				return
			case 'color':
				chain.setColor(value).run()
				return
			default:
				chain
					.setMark('textStyle', {
						[property]: value,
					})
					.run()
				return
		}
	}

	const initTextEditor = (content) => {
		return new Editor({
			extensions: extensions,
			editable: false,
			content: content,
			onTransaction: ({ transaction, editor }) => update({ transaction, editor }),
			onSelectionUpdate: ({ editor }) => update({ transaction: editor.state.tr, editor }),
		})
	}

	watch(
		() => activeEditor.value,
		(newEditor) => {
			setEditorStyles(newEditor)
		},
	)

	return {
		activeEditor,
		editorStyles,
		toggleMark,
		updateProperty,
		initTextEditor,
	}
}
