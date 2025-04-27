import { ref, computed, nextTick } from 'vue'
import { call } from 'frappe-ui'

import { slide, slideBounds } from './slide'

import { generateUniqueId } from '../utils/helpers'
import { guessTextColorFromBackground } from '../utils/color'

const activeElementIds = ref([])
const focusElementId = ref(null)
const pairElementId = ref(null)

const activeElements = computed(() => {
	let elements = []
	slide.value.elements.forEach((element) => {
		if (activeElementIds.value.includes(element.id)) {
			elements.push(element)
		}
	})
	return elements
})

const activeElement = computed(() => {
	if (focusElementId.value) {
		return slide.value.elements.find((element) => element.id === focusElementId.value)
	} else {
		return activeElements.value[0]
	}
})

const setActiveElements = (ids, focus = false) => {
	if (ids.length == 1 && focus) {
		activeElementIds.value = []
		focusElementId.value = ids[0]
	} else {
		if (ids.length == 1 && activeElementIds.value.includes(ids[0])) return
		activeElementIds.value = ids
		focusElementId.value = null
	}
}

const addTextElement = (text) => {
	const lastTextElement = slide.value.elements.reverse().find((element) => element.type == 'text')

	const element = {
		id: generateUniqueId(),
		left: 100,
		top: 100,
		content: text || 'Text',
		type: 'text',
		textAlign: 'center',
	}

	if (lastTextElement) {
		element.fontSize = lastTextElement.fontSize
		element.fontFamily = lastTextElement.fontFamily
		element.fontWeight = lastTextElement.fontWeight
		element.color = lastTextElement.color
		element.lineHeight = lastTextElement.lineHeight
		element.letterSpacing = lastTextElement.letterSpacing
		element.opacity = lastTextElement.opacity
	} else {
		const slideColor = document.querySelector('.slide')?.style.backgroundColor
		element.fontSize = 30
		element.fontFamily = 'Inter'
		element.fontWeight = 'normal'
		element.color = guessTextColorFromBackground(slideColor)
		element.lineHeight = 1
		element.letterSpacing = 0
		element.opacity = 100
	}
	slide.value.elements.push(element)
	nextTick(() => setActiveElements([element.id]))
}

const addMediaElement = (file, type) => {
	let element = {
		id: generateUniqueId(),
		width: 300,
		left: 200,
		top: 75,
		opacity: 100,
		type: type,
		src: file.file_url,
		file_name: file.name,
		borderStyle: 'none',
		borderWidth: 0,
		borderRadius: 0,
		borderColor: '#000000',
		shadowOffsetX: 0,
		shadowOffsetY: 0,
		shadowSpread: 0,
		shadowColor: '#000000',
	}
	if (type == 'video') {
		element.autoplay = false
		element.loop = false
		element.playbackRate = 1
	}
	slide.value.elements.push(element)
	nextTick(() => setActiveElements([element.id]))
}

const duplicateElements = async (e, elements) => {
	e.preventDefault()

	let newSelection = []
	const oldElements = elements
	activeElementIds.value = []

	await nextTick()

	oldElements.forEach((element) => {
		let newElement = JSON.parse(JSON.stringify(element))
		newElement.id = generateUniqueId()
		newElement.top += 40
		newElement.left += 40
		slide.value.elements.push(newElement)
		newSelection.push(newElement.id)
	})

	nextTick(() => (activeElementIds.value = newSelection))
}

const deleteElements = async (e) => {
	activeElements.value.forEach((element) => {
		if (['image', 'video'].includes(element.type)) {
			call('frappe.client.delete', {
				doctype: 'File',
				name: element.file_name,
			})
		}
	})
	const idsToDelete = activeElementIds.value
	resetFocus()
	nextTick(() => {
		slide.value.elements = slide.value.elements.filter((element) => {
			return !idsToDelete.includes(element.id)
		})
	})
}

const selectAllElements = () => {
	activeElementIds.value = slide.value.elements.map((element) => element.id)
}

const resetFocus = () => {
	activeElementIds.value = []
	focusElementId.value = null
	pairElementId.value = null
}

const toggleTextProperty = (property, value) => {
	const oldStyle = activeElement.value[property]
	let newStyle = ''

	switch (property) {
		case 'fontWeight':
			newStyle = oldStyle == 'bold' ? 'normal' : 'bold'
			break
		case 'fontStyle':
			newStyle = oldStyle == 'italic' ? 'normal' : 'italic'
			break
		case 'textTransform':
			newStyle = oldStyle == 'uppercase' ? 'none' : 'uppercase'
			break
		default:
			if (!oldStyle) {
				newStyle = value
				break
			}
			newStyle = oldStyle.includes(value)
				? oldStyle.replace(value, '')
				: oldStyle + ' ' + value
	}
	activeElement.value[property] = newStyle
}

const moveElement = (elementId, movement) => {
	let element = slide.value.elements.find((el) => el.id === elementId)

	element.left += movement.dx
	element.top += movement.dy
}

const resizeElement = (elementId, dimensions) => {
	let element = slide.value.elements.find((el) => el.id == elementId)

	if (element && dimensions.width != element.width) {
		const newWidth = dimensions.width / slideBounds.scale
		element.width = newWidth
	}
}

const getElementPosition = (elementId) => {
	const elementRect = document
		.querySelector(`[data-index="${elementId}"]`)
		.getBoundingClientRect()

	const elementLeft = (elementRect.left - slideBounds.left) / slideBounds.scale
	const elementTop = (elementRect.top - slideBounds.top) / slideBounds.scale
	const elementRight = elementLeft + elementRect.width / slideBounds.scale
	const elementBottom = elementTop + elementRect.height / slideBounds.scale

	return {
		left: elementLeft,
		top: elementTop,
		right: elementRight,
		bottom: elementBottom,
	}
}

const getCopiedJSON = () => {
	const elementsCopy = JSON.parse(JSON.stringify(activeElements.value))
	elementsCopy.forEach((element) => {
		const { left, top } = getElementPosition(element.id)
		element.left = left
		element.top = top
	})
	return JSON.stringify(elementsCopy)
}

const handleCopy = (e) => {
	e.preventDefault()
	const clipboardJSON = getCopiedJSON()
	e.clipboardData.setData('application/json', clipboardJSON)
}

const pasteText = (clipboardText) => {
	if (focusElementId.value) {
		document.execCommand('insertText', false, clipboardText)
	} else {
		resetFocus()
		addTextElement(clipboardText)
	}
}

const pasteElements = (e, clipboardJSON) => {
	const elements = JSON.parse(clipboardJSON)
	duplicateElements(e, elements)
}

const handlePaste = (e) => {
	e.preventDefault()

	const clipboardText = e.clipboardData.getData('text/plain')
	if (clipboardText) {
		return pasteText(clipboardText)
	}

	const clipboardJSON = e.clipboardData.getData('application/json')
	if (clipboardJSON) {
		return pasteElements(e, clipboardJSON)
	}
}

export {
	activeElementIds,
	focusElementId,
	pairElementId,
	activeElements,
	activeElement,
	setActiveElements,
	resetFocus,
	addTextElement,
	addMediaElement,
	duplicateElements,
	deleteElements,
	selectAllElements,
	toggleTextProperty,
	moveElement,
	resizeElement,
	getElementPosition,
	handleCopy,
	handlePaste,
}
