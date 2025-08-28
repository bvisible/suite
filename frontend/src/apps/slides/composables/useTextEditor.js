import { ref, reactive, watch } from 'vue'
import { Editor } from '@tiptap/vue-3'
import { extensions } from '@/stores/tiptapSetup'
import { TextSelection } from 'prosemirror-state'
import { activeElement } from '@/stores/element'

export const activeEditor = ref(null)

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

export const lastUsedStyles = reactive({ ...editorStyles })

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
			opacity: activeStyles.opacity,
		})
	}

	const applyLastUsedStyles = (editor) => {
		const oldStyles = JSON.parse(JSON.stringify(lastUsedStyles))

		let chain = editor.chain().focus()

		if (oldStyles.textAlign) chain = chain.setTextAlign(oldStyles.textAlign)
		if (oldStyles.color) chain = chain.setColor(oldStyles.color)

		chain = chain.setMark('textStyle', {
			fontSize: oldStyles.fontSize,
			fontFamily: oldStyles.fontFamily,
			letterSpacing: oldStyles.letterSpacing,
			opacity: oldStyles.opacity,
			textTransform: oldStyles.uppercase ? 'uppercase' : null,
		})

		if (oldStyles.bold) chain = chain.setBold()
		if (oldStyles.italic) chain = chain.setItalic()
		if (oldStyles.underline) chain = chain.setUnderline()
		if (oldStyles.strike) chain = chain.setStrike()

		chain.run()
	}

	let isRestoringStyles = false

	const updateElementContent = (editor) => {
		const didStylesChange = Object.keys(lastUsedStyles).some((key) => {
			return lastUsedStyles[key] != editorStyles[key]
		})

		if (didStylesChange) {
			activeElement.value.content = editor.getHTML()
		}
	}

	const updateLastUsedStyles = () => {
		for (const key in editorStyles) {
			lastUsedStyles[key] = editorStyles[key]
		}
	}

	const updateEditor = ({ transaction, editor }) => {
		if (transaction.docChanged) {
			const textContent = editor.getText().trim()

			if (textContent.length == 0 && !isRestoringStyles) {
				isRestoringStyles = true
				applyLastUsedStyles(editor)
				setTimeout(() => {
					isRestoringStyles = false
				}, 0)

				return
			}

			setEditorStyles(editor)
			updateElementContent(editor)
			updateLastUsedStyles(editor)
		} else if (transaction.selectionSet) {
			setEditorStyles(editor)
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

	const setLineHeight = (value) => {
		if (!activeElement.value) return

		activeElement.value.editorMetadata = {
			...activeElement.value.editorMetadata,
			lineHeight: value,
		}

		const el = activeEditor.value.view.dom
		if (el) el.style.lineHeight = value
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
				break
			case 'color':
				chain.setColor(value).run()
				break
			case 'lineHeight':
				setLineHeight(value)
				break
			default:
				chain
					.setMark('textStyle', {
						[property]: value,
					})
					.run()
				break
		}
	}

	const getEditorProps = (editorMetadata) => {
		return {
			attributes: {
				style: `line-height: ${editorMetadata?.lineHeight || 1.5}`,
			},
		}
	}

	const initTextEditor = (id, content, editorMetadata, isEditable = false) => {
		activeEditor.value = new Editor({
			extensions: extensions,
			editable: isEditable,
			content: content,
			editorProps: getEditorProps(editorMetadata),
			onTransaction: ({ transaction, editor }) => updateEditor({ transaction, editor }),
		})
	}

	watch(
		() => activeEditor.value,
		(newEditor) => {
			setEditorStyles(newEditor)
			for (const key in editorStyles) {
				lastUsedStyles[key] = editorStyles[key]
			}
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
