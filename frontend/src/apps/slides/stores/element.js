import { ref, computed, nextTick } from 'vue'
import { call } from 'frappe-ui'
import { inSlideShow, slideFocus, slide } from './slide'
import { guessTextColorFromBackground } from '../utils/color'

const currentDataIndex = ref(null)
const currentFocusedIndex = ref(null)
const currentPairedDataIndex = ref(null)

const activeElement = computed({
	get() {
		return (
			slide.value.elements[currentDataIndex.value] ||
			slide.value.elements[currentFocusedIndex.value]
		)
	},
	set(newValue) {
		slide.value.elements[currentDataIndex.value] = newValue
	},
})

const setActiveElement = (index, focus = false) => {
	if (inSlideShow.value) return

	if (activeElement.value && currentFocusedIndex.value) {
		const newContent = document.querySelector(
			`[data-index="${currentFocusedIndex.value}"]`,
		).innerText
		activeElement.value = { ...activeElement.value, content: newContent }
	}
	if (focus) {
		currentFocusedIndex.value = index
		currentDataIndex.value = null
	} else {
		currentDataIndex.value = index
		currentFocusedIndex.value = null
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
	}

	if (lastTextElement) {
		element.width = lastTextElement.width
		element.fontSize = lastTextElement.fontSize
		element.fontFamily = lastTextElement.fontFamily
		element.fontWeight = lastTextElement.fontWeight
		element.color = lastTextElement.color
		element.lineHeight = lastTextElement.lineHeight
		element.letterSpacing = lastTextElement.letterSpacing
	} else {
		const slideColor = document.querySelector('.slide')?.style.backgroundColor
		element.width = 65
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
	nextTick(() => (currentDataIndex.value = slide.value.elements.indexOf(newElement)))
}

const deleteElement = async (e) => {
	if (['image', 'video'].includes(activeElement.value.type)) {
		await call('frappe.client.delete', {
			doctype: 'File',
			name: activeElement.value.file_name,
		})
	}
	slide.value.elements.splice(currentDataIndex.value, 1)
	resetFocus()
}

const resetFocus = () => {
	currentDataIndex.value = null
	currentFocusedIndex.value = null
	currentPairedDataIndex.value = null
}

export {
	currentDataIndex,
	currentFocusedIndex,
	currentPairedDataIndex,
	activeElement,
	setActiveElement,
	resetFocus,
	addTextElement,
	addMediaElement,
	duplicateElement,
	deleteElement,
}
