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
import { TextSelection } from 'prosemirror-state'

import { getDocFromHTML } from '@/utils/helpers'

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
	// needed to ensure that <li> tag renders the span styles (e.g. font size, color etc.)
	// they need to be present at <li> level so that CSS ::before element can work for bullet styling
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

const handleListItemEnterKey = (editor, pos, marks) => {
	const { state, view } = editor

	const endPos = pos.end()

	// before splitting to next list item, insert ZWSP at end of current item
	// move cursor to end of current item and then split
	// so new list already has placeholder

	let tr = state.tr.insertText(ZWSP, endPos, endPos, marks)
	tr = tr.setSelection(TextSelection.create(tr.doc, endPos))
	view.dispatch(tr)

	// intentional since if we split and then add placeholder
	// ProseMirror will not automatically re-trigger renderHTML for CustomListItem - line 122
	editor.commands.splitListItem('listItem')

	return true
}

const addEmptyLineBefore = (state, view, pos, marks) => {
	const startOfCurrentPos = pos.start()
	const $before = state.doc.resolve(startOfCurrentPos - 1)
	const prevNode = $before.nodeBefore

	if (prevNode && !prevNode.isTextblock) return false

	let tr = view.state.tr
	const prevEnd = startOfCurrentPos - 1
	// insert ZWSP inside previous node as placeholder so
	// <br class="ProseMirror-trailingBreak"> is not added
	tr.insert(prevEnd + 1, state.schema.text(ZWSP, marks))
	tr = tr.setStoredMarks(marks)
	view.dispatch(tr)
	return true
}

const getCursorPositionFlags = (pos) => {
	const parent = pos.parent

	return {
		isCursorAtStart: pos.parentOffset === 0,
		isCursorAtEnd: pos.parentOffset === parent.content.size,
	}
}

const handleEnterKey = (editor) => {
	const { state, view } = editor
	const { selection, storedMarks } = state
	const $pos = selection.$from

	const marks = storedMarks || $pos.marks()

	if (isInList($pos)) {
		return handleListItemEnterKey(editor, $pos, marks)
	}

	const didSplit = editor.commands.splitBlock()

	// splitting to new line failed so don't change anything
	if (!didSplit) return false

	const { isCursorAtStart, isCursorAtEnd } = getCursorPositionFlags($pos)

	let tr = view.state.tr

	if (isCursorAtStart) {
		return addEmptyLineBefore(state, view, $pos, marks)
	} else if (isCursorAtEnd) {
		tr.insertText(ZWSP)
	}

	// re-apply marks to new span (created after split)
	tr = tr.setStoredMarks(marks)

	view.dispatch(tr)

	return true
}

function getFirstTextNodeInsideSelection(state) {
	const { from, to } = state.selection
	let foundText = null

	state.doc.nodesBetween(from, to, (node) => {
		if (node.isText) {
			foundText = node
			return false
		}
	})

	return foundText
}

const getMarksForPlaceholder = (state) => {
	let marks = state.storedMarks || state.selection.$from.marks()

	if (!marks || marks.length === 0) {
		const firstText = getFirstTextNodeInsideSelection(state)
		marks = firstText ? firstText.marks : []
	}

	return marks
}

const addPlaceholderAndRetainMarks = (event, view, start, end) => {
	event.preventDefault()

	const state = view.state
	const marks = getMarksForPlaceholder(state)

	let tr = state.tr
	tr = tr.replaceWith(start, end, state.schema.text(ZWSP, marks))
	tr = tr.setStoredMarks(marks)
	tr = tr.setSelection(TextSelection.create(tr.doc, start + 1))
	view.dispatch(tr)

	return true
}

const removePlaceholderAndJoinBackward = (event, view, start, end) => {
	event.preventDefault()

	let tr = view.state.tr.delete(start, end)
	view.dispatch(tr)

	joinBackward(view.state, view.dispatch)

	return true
}

const getSelectionRange = (selection) => {
	const $from = selection.$from
	const $to = selection.$to

	return {
		from: $from.pos,
		to: $to.pos,
		start: $from.start(),
		end: $from.end(),
	}
}

const getTextForSelection = ($from) => {
	return $from.parent.textContent || ''
}

const getPrevNode = ($from, view) => {
	const blockDepth = $from.depth
	const posBeforeBlock = $from.before(blockDepth)

	const resolved = view.state.doc.resolve(posBeforeBlock)
	return resolved.nodeBefore
}

const joinBackwardAfterPlaceholder = (view) => {
	joinBackward(view.state, view.dispatch)

	let tr = view.state.tr
	const newPos = view.state.selection.$from.pos
	tr = tr.delete(newPos - 1, newPos)
	view.dispatch(tr)

	return true
}

const handleKeyDown = (view, event) => {
	if (event.key !== 'Backspace') return false

	const { selection } = view.state
	const $from = selection.$from

	if (isInList($from)) return false

	const text = getTextForSelection($from)
	if (text === undefined) return false

	const { from, to, start, end } = getSelectionRange(selection)

	const lastCharOnLine = text.length === 1 && text !== ZWSP
	const isEntireParagraphSelected = from === start && to === end
	const isFullDocSelected = from === 0 && to === view.state.doc.content.size

	if (lastCharOnLine || isEntireParagraphSelected || isFullDocSelected) {
		// if the last non-ZWSP character is being deleted, replace with ZWSP + re-apply marks
		// so <br class="ProseMirror-trailingBreak"> is not added
		return addPlaceholderAndRetainMarks(event, view, start, end)
	}

	const prevNode = getPrevNode($from, view)

	if (text === ZWSP && prevNode && prevNode.isTextblock) {
		// if only ZWSP is present, default behavior will lead to
		// deleting it and adding <br class="ProseMirror-trailingBreak">
		// so manually delete ZWSP and join with previous line which is expected behavior without the placeholder
		return removePlaceholderAndJoinBackward(event, view, start, end)
	}

	if (text === ZWSP) {
		// if only ZWSP is present but no previous textblock, do nothing
		event.preventDefault()
		return true
	}

	if (prevNode && prevNode.isTextblock && prevNode.textContent === ZWSP) {
		return joinBackwardAfterPlaceholder(event, view, $from)
	}

	return false
}

const removePlaceholderAndInsertText = (view, pos, text) => {
	const { state, dispatch } = view
	const { selection, storedMarks } = state

	const marks = storedMarks || selection.$from.marks()

	// remove ZWSP when user enters actual text
	let tr = state.tr

	tr = tr.delete(pos.pos - 1, pos.pos)
	tr = tr.setStoredMarks(marks)
	tr = tr.insertText(text)

	dispatch(tr)

	return true
}

const handleTextInput = (view, from, to, text) => {
	const $pos = view.state.selection.$from
	const nodeBefore = $pos.nodeBefore

	// if the prev char is not ZWSP, use default behavior
	if (!nodeBefore || nodeBefore.text !== ZWSP) return false

	return removePlaceholderAndInsertText(view, $pos, text)
}

const styledEmptyLinePlugin = new Plugin({
	key: new PluginKey('styledEmptyLinePlugin'),
	props: {
		// before adding an unstyled empty line on clearing content
		// add a ZWSP with stored marks to retain styles
		handleKeyDown,
		// before typing new text to styled empty line
		// remove the placeholder ZWSP
		handleTextInput,
	},
})

const StyledEmptyLine = Extension.create({
	name: 'StyledEmptyLine',

	addKeyboardShortcuts() {
		return {
			// insert ZWSP char so ProseMirror does not add <br class="ProseMirror-trailingBreak">
			// instead adds an empty styled span - so line height, font size etc. are consistent
			Enter: ({ editor }) => handleEnterKey(editor),
		}
	},

	addProseMirrorPlugins() {
		return [styledEmptyLinePlugin]
	},
})

const updateParagraphHTML = (doc, p, prevSpanStyles) => {
	p.innerHTML = ''

	const span = doc.createElement('span')
	span.setAttribute('style', prevSpanStyles)
	span.innerHTML = ZWSP

	p.appendChild(span)
}

export const patchEmptyParagraphs = (htmlString) => {
	// to patch <br class="ProseMirror-trailingBreak"> -> ZWSP
	// before StyledEmptyLine plugin was added
	let didUpdate = false

	const doc = getDocFromHTML(htmlString)

	const allParagraphs = Array.from(doc.body.querySelectorAll('p'))
	let prevSpanStyles = null

	allParagraphs.forEach((p) => {
		const isEmpty = p.textContent.trim() === ''
		const firstSpan = p.querySelector('span')

		if (!isEmpty && firstSpan) {
			prevSpanStyles = firstSpan.getAttribute('style') || ''
			return
		}

		if (isEmpty && prevSpanStyles) {
			if (!didUpdate) didUpdate = true

			updateParagraphHTML(doc, p, prevSpanStyles)
		}
	})

	return {
		wasUpdated: didUpdate,
		updatedHTML: didUpdate ? doc.body.innerHTML : htmlString,
	}
}

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
