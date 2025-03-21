import { ref, computed, nextTick } from 'vue'
import { call } from 'frappe-ui'

import { slide } from './slide'

import { generateUniqueId } from '../utils/helpers'
import { guessTextColorFromBackground } from '../utils/color'

const activePosition = ref(null)
const activeDimensions = ref(null)

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

const addTextElement = () => {
	const lastTextElement = slide.value.elements.reverse().find((element) => element.type == 'text')

	const element = {
		id: generateUniqueId(),
		left: 100,
		top: 100,
		content: 'Text',
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
		element.autoPlay = false
		element.loop = false
		element.playbackRate = 1
	}
	slide.value.elements.push(element)
	nextTick(() => setActiveElements([element.id]))
}

const duplicateElements = async (e) => {
	e.preventDefault()

	let newSelection = []
	const oldElements = activeElements.value
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
	const oldStyle = activeElements.value[0][property]
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
	let element = slide.value.elements.find((element) => element.id == activeElementIds.value[0])
	element[property] = newStyle
}

const moveElement = (elementId, movement) => {
	let element = slide.value.elements.find((el) => el.id === elementId)

	element.left += movement.dx
	element.top += movement.dy
}

const updateActivePosition = (positionChange) => {
	activePosition.value = {
		left: activePosition.value?.left + positionChange.dx,
		top: activePosition.value?.top + positionChange.dy,
	}
}

export {
	activePosition,
	activeDimensions,
	activeElementIds,
	focusElementId,
	pairElementId,
	activeElements,
	setActiveElements,
	resetFocus,
	addTextElement,
	addMediaElement,
	duplicateElements,
	deleteElements,
	selectAllElements,
	toggleTextProperty,
	moveElement,
	updateActivePosition,
}
