import { ref, onMounted, onUnmounted } from 'vue'
import { TextSelection } from 'prosemirror-state'

const activeEditor = ref(null)

export const useTextEditor = () => {
	const editorStyles = ref({
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

	const update = () => {
		if (!activeEditor.value) return

		const editor = activeEditor.value
		const activeStyles = editor.getAttributes('textStyle')

		editorStyles.value = {
			bold: editor.isActive('bold'),
			italic: editor.isActive('italic'),
			strike: editor.isActive('strike'),
			underline: editor.isActive('underline'),
			bulletList: editor.isActive('bulletList'),
			orderedList: editor.isActive('orderedList'),
			uppercase: activeStyles.textTransform == 'uppercase',
			textAlign: editor.getAttributes('paragraph').textAlign || 'left',
			fontSize: parseInt(activeStyles.fontSize, 10) || null,
			fontFamily: activeStyles.fontFamily || null,
			color: activeStyles.color || null,
			lineHeight: activeStyles.lineHeight,
			letterSpacing: parseInt(activeStyles.letterSpacing, 10),
			opacity: parseInt(activeStyles.opacity, 10),
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

	const changeListMarkers = (property, value) => {
		activeEditor.value.commands.command(({ tr, state }) => {
			const listItemType = state.schema.nodes.listItem

			tr.doc.descendants((node, pos) => {
				if (node.type === listItemType) {
					const currentStyle = typeof node.attrs.style == 'string' ? node.attrs.style : ''

					const newStyle = getCSSString(currentStyle, property, value)

					tr.setNodeMarkup(pos, listItemType, {
						...node.attrs,
						style: newStyle,
					})
				}
			})

			return true
		})
	}

	const setListProperty = (chain) => {
		if (!activeEditor.value.isEditable) selectListBlock()

		if (!activeEditor.value.isActive('orderedList')) {
			activeEditor.value.chain().focus().wrapInList('orderedList').run()
		} else {
			activeEditor.value.chain().focus().liftListItem('listItem').run()
		}
	}

	const initListMarkers = (chain) => {
		changeListMarkers('fontSize', editorStyles.value.fontSize)
		changeListMarkers('fontFamily', editorStyles.value.fontFamily)
		changeListMarkers('color', editorStyles.value.color)
		changeListMarkers('opacity', editorStyles.value.opacity)
	}

	const updateProperty = (property, value) => {
		const currentEditor = activeEditor.value

		const chain = currentEditor.chain().focus()

		if (property == 'list') {
			setListProperty(chain)
			initListMarkers(chain)
			return
		}

		const { empty } = currentEditor.state.selection
		if (empty) chain.selectAll()

		switch (property) {
			case 'textAlign':
				chain.setTextAlign(value).run()
				break
			case 'color':
				chain.setColor(value).run()
				break
			default:
				chain
					.setMark('textStyle', {
						[property]: value,
					})
					.run()
				break
		}

		changeListMarkers(property, value)
	}

	onMounted(() => {
		if (!activeEditor.value) return
		activeEditor.value.on('selectionUpdate', update)
		activeEditor.value.on('transaction', update)
		update()
	})

	onUnmounted(() => {
		if (!activeEditor.value) return
		activeEditor.value.off('selectionUpdate', update)
		activeEditor.value.off('transaction', update)
	})

	return {
		activeEditor,
		editorStyles,
		toggleMark,
		updateProperty,
	}
}
