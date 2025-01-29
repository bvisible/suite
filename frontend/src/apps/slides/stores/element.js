import { ref, computed, nextTick } from 'vue'
import { call } from 'frappe-ui'

import { inSlideShow } from './presentation'
import { slideFocus, slide } from './slide'

import { guessTextColorFromBackground } from '../utils/color'

const activePosition = ref(null)
const activeDimensions = ref(null)

const activeElementId = ref(null)
const focusElementId = ref(null)
const pairElementId = ref(null)

const activeElement = computed({
	get() {
		return (
			slide.value.elements[activeElementId.value] ||
			slide.value.elements[focusElementId.value]
		)
	},
	set(newValue) {
		slide.value.elements[activeElementId.value] = newValue
	},
})

const setActiveElement = (index, focus = false) => {
	if (inSlideShow.value) return

	if (activeElement.value && focusElementId.value) {
		const newContent = document.querySelector(
			`[data-index="${focusElementId.value}"]`,
		).innerText
		activeElement.value = { ...activeElement.value, content: newContent }
	}
	if (focus) {
		focusElementId.value = index
		activeElementId.value = null
	} else {
		activeElementId.value = index
		focusElementId.value = null
	}
	slideFocus.value = false
}

const addTextElement = () => {
	const lastTextElement = slide.value.elements.reverse().find((element) => element.type == 'text')

	const element = {
		left: 100,
		top: 100,
		opacity: 100,
		content: 'Text',
		type: 'text',
		width: 'auto',
	}

	if (lastTextElement) {
		element.fontSize = lastTextElement.fontSize
		element.fontFamily = lastTextElement.fontFamily
		element.fontWeight = lastTextElement.fontWeight
		element.color = lastTextElement.color
		element.lineHeight = lastTextElement.lineHeight
		element.letterSpacing = lastTextElement.letterSpacing
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
	nextTick(() => setActiveElement(slide.value.elements.length - 1))
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
	nextTick(() => setActiveElement(element))
}

const duplicateElement = (e) => {
	e.preventDefault()
	let newElement = JSON.parse(JSON.stringify(activeElement.value))
	newElement.top += 40
	newElement.left += 40
	slide.value.elements.push(newElement)
	nextTick(() => (activeElementId.value = slide.value.elements.indexOf(newElement)))
}

const deleteElement = async (e) => {
	if (['image', 'video'].includes(activeElement.value.type)) {
		await call('frappe.client.delete', {
			doctype: 'File',
			name: activeElement.value.file_name,
		})
	}
	slide.value.elements.splice(activeElementId.value, 1)
	resetFocus()
}

const resetFocus = () => {
	activeElementId.value = null
	focusElementId.value = null
	pairElementId.value = null
}

export {
	activePosition,
	activeDimensions,
	activeElementId,
	focusElementId,
	pairElementId,
	activeElement,
	setActiveElement,
	resetFocus,
	addTextElement,
	addMediaElement,
	duplicateElement,
	deleteElement,
}
