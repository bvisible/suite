import { ref, computed, nextTick } from 'vue'
import { call } from 'frappe-ui'

import { slideFocus, slide } from './slide'

import { guessTextColorFromBackground } from '../utils/color'

const activePosition = ref(null)
const activeDimensions = ref(null)

const activeElementIds = ref([])
const focusElementId = ref(null)
const pairElementId = ref(null)

const activeElements = computed(() => {
	let elements = []
	slide.value.elements.forEach((element, index) => {
		if (activeElementIds.value.includes(index)) {
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
	slideFocus.value = false
}

const addTextElement = () => {
	const lastTextElement = slide.value.elements.reverse().find((element) => element.type == 'text')

	const element = {
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
	nextTick(() => setActiveElements([slide.value.elements.length - 1]))
}

const addMediaElement = (file, type) => {
	let element = {
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
	nextTick(() => setActiveElements([slide.value.elements.length - 1]))
}

const duplicateElements = async (e) => {
	e.preventDefault()

	let newSelection = []
	const oldElements = activeElements.value
	activeElementIds.value = []

	await nextTick()

	oldElements.forEach((element) => {
		let newElement = JSON.parse(JSON.stringify(element))
		newElement.top += 40
		newElement.left += 40
		slide.value.elements.push(newElement)
		newSelection.push(slide.value.elements.indexOf(newElement))
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
		slide.value.elements = slide.value.elements.filter((_, index) => {
			return !idsToDelete.includes(index)
		})
	})
}

const selectAllElements = () => {
	activeElementIds.value = slide.value.elements.map((_, index) => index)
}

const resetFocus = () => {
	activeElementIds.value = []
	focusElementId.value = null
	pairElementId.value = null
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
}
