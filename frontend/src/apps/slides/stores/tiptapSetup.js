import { Editor } from '@tiptap/vue-3'
import { Extension } from '@tiptap/core'

import StarterKit from '@tiptap/starter-kit'
import TextStyle from '@tiptap/extension-text-style'
import TextAlign from '@tiptap/extension-text-align'
import Underline from '@tiptap/extension-underline'
import BulletList from '@tiptap/extension-bullet-list'
import OrderedList from '@tiptap/extension-ordered-list'
import ListItem from '@tiptap/extension-list-item'
import Color from '@tiptap/extension-color'
import { Plugin, PluginKey } from 'prosemirror-state'
import { joinBackward } from 'prosemirror-commands'

const parseElementStyle = (attribute, value) => {
	if (!value) return null

	if (attribute == 'opacity') {
		const val = parseFloat(value)
		return isNaN(val) ? null : Math.round(val * 100)
	}

	return value
}

const renderAttributeHTML = (attribute, value) => {
	const suffixes = {
		fontSize: 'px',
		letterSpacing: 'px',
	}

	const name = attribute.replace(/([A-Z])/g, '-$1').toLowerCase()

	if (attribute == 'opacity') {
		value = Number(value) / 100
		return { style: `${name}: ${value}` }
	}

	const suffix = suffixes[attribute] || ''
	const skipSuffix = typeof value == 'string' && value.includes(suffix)
	value = skipSuffix ? value : `${value}${suffix}`

	return value ? { style: `${name}: ${value}` } : {}
}

const CustomTextStyle = TextStyle.extend({
	addAttributes() {
		const attrs = {}

		const attributesList = [
			'fontSize',
			'textTransform',
			'fontFamily',
			'letterSpacing',
			'opacity',
		]

		attributesList.forEach((attr) => {
			attrs[attr] = {
				default: null,
				parseHTML: (element) => parseElementStyle(attr, element.style[attr]),
				renderHTML: (attributes) => renderAttributeHTML(attr, attributes[attr]),
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

const getItemAttributes = (node) => {
	const paragraphNode = node.content?.firstChild
	const textNode = paragraphNode?.firstChild

	const attrs = {
		color: null,
		fontSize: null,
		fontFamily: null,
		letterSpacing: null,
		opacity: null,
	}

	if (textNode?.marks) {
		for (const mark of textNode.marks) {
			if (mark.type.name == 'textStyle') {
				const styleAttrs = mark.attrs
				styleAttrs.fontSize = parseInt(styleAttrs.fontSize)
				Object.assign(attrs, styleAttrs)
				return attrs
			}
		}
	}

	return attrs
}

const CustomListItem = ListItem.extend({
	renderHTML({ node, HTMLAttributes, ...rest }) {
		const liAttrs = { ...HTMLAttributes }

		const { color, fontSize, fontFamily, letterSpacing, opacity } = getItemAttributes(node)

		liAttrs.style = [
			liAttrs.style || '',
			`color: ${color};`,
			`font-size: ${fontSize}px;`,
			`font-family: ${fontFamily};`,
			`letter-spacing: ${letterSpacing};`,
			`opacity: ${opacity};`,
		].join(' ')

		return ['li', liAttrs, 0]
	},
})

const ZWSP = '\u200B'

const isInList = ($pos) => {
	// intentional since <li> is not direct parent of text node
	for (let d = $pos.depth; d > 0; d--) {
		const node = $pos.node(d)
		if (node.type.name === 'listItem') return true
	}
	return false
}

const handleEnterKey = (editor) => {
	const { state, view } = editor
	const { selection, storedMarks } = state
	const $pos = selection.$from

	if (isInList($pos)) return false

	// fetch current marks before splitting to next line
	const marks = storedMarks || $pos.marks()

	const didSplit = editor.commands.splitBlock()

	// splitting to new line failed so don't change anything
	if (!didSplit) return false

	const parent = $pos.parent
	const cursorAtStart = $pos.parentOffset === 0
	const cursorAtEnd = $pos.parentOffset === parent.content.size

	// insert ZWSP char so ProseMirror does not add <br class="ProseMirror-trailingBreak">
	// instead adds an empty styled span - so line height, font size etc. are consistent
	let tr = view.state.tr

	if (cursorAtStart) {
		const startOfCurrentPos = $pos.start()
		const $before = state.doc.resolve(startOfCurrentPos - 1)
		const prevNode = $before.nodeBefore

		if (prevNode && prevNode.isTextblock) {
			const prevEnd = startOfCurrentPos - 1
			// insert ZWSP inside previous node as placeholder so
			// <br class="ProseMirror-trailingBreak"> is not added
			tr.insert(prevEnd + 1, state.schema.text(ZWSP, marks))
			tr = tr.setStoredMarks(marks)
			view.dispatch(tr)
			return true
		}
	} else if (cursorAtEnd) {
		tr.insertText(ZWSP)
	}

	// re-apply marks to new span (created after split)
	tr = tr.setStoredMarks(marks)

	view.dispatch(tr)

	return true
}

const handleKeyDown = (view, event) => {
	if (event.key !== 'Backspace') return false

	const { state, dispatch } = view
	const { selection, storedMarks } = state

	const $from = selection.$from
	const $to = selection.$to

	if (isInList($from)) return false

	const firstChild = $from.parent.content.firstChild
	if (!firstChild || !firstChild.isText) return false

	const text = firstChild.text
	const marks = storedMarks || $from.marks()

	const start = $from.start()
	const end = $from.end()

	const from = $from.pos
	const to = $to.pos

	// if the last non-ZWSP character is being deleted, replace with ZWSP + re-apply marks
	// so <br class="ProseMirror-trailingBreak"> is not added
	if ((text.length === 1 && text !== ZWSP) || (from === start && to === end)) {
		event.preventDefault()

		let tr = state.tr
		tr = tr.replaceWith(start, end, state.schema.text(ZWSP, marks))
		tr = tr.setStoredMarks(marks)

		dispatch(tr)

		return true
	}

	if (text === ZWSP) {
		// if only ZWSP is present, default behavior will lead to
		// deleting it and adding <br class="ProseMirror-trailingBreak">
		// so manually delete ZWSP and join with previous line which is expected behavior without the placeholder

		event.preventDefault()

		let tr = state.tr.delete(start, end)
		dispatch(tr)

		joinBackward(view.state, view.dispatch)

		return true
	}

	return false
}

const handleTextInput = (view, from, to, text) => {
	const { state, dispatch } = view
	const { selection, storedMarks } = state
	const marks = storedMarks || selection.$from.marks()

	const $pos = selection.$from
	const nodeBefore = $pos.nodeBefore

	// if the prev char is not ZWSP, use default behavior
	if (!nodeBefore || nodeBefore.text !== ZWSP) return false

	// remove ZWSP when user enters actual text
	let tr = state.tr

	tr = tr.delete($pos.pos - 1, $pos.pos)
	tr = tr.setStoredMarks(marks)
	tr = tr.insertText(text)

	dispatch(tr)

	return true
}

export const StyledEmptyLine = Extension.create({
	name: 'StyledEmptyLine',

	addKeyboardShortcuts() {
		return {
			Enter: ({ editor }) => handleEnterKey(editor),
		}
	},

	addProseMirrorPlugins() {
		return [
			new Plugin({
				key: new PluginKey('styledSpanPlugin'),
				props: {
					// before adding an unstyled empty line on clearing content
					// add a ZWSP with stored marks to retain styles
					handleKeyDown,
					// before typing new text to styled empty line
					// remove the placeholder ZWSP
					handleTextInput,
				},
			}),
		]
	},
})

export const extensions = [
	StarterKit.configure({
		bulletList: false,
		orderedList: false,
		listItem: false,
	}),
	CustomTextStyle,
	Underline,
	Color,
	TextAlign.configure({
		types: ['paragraph'],
	}),
	PastePlainText,
	BulletList.configure({
		keepAttributes: true,
		keepMarks: true,
	}),
	OrderedList.configure({
		keepAttributes: true,
		keepMarks: true,
	}),
	CustomListItem,
	StyledEmptyLine,
]
