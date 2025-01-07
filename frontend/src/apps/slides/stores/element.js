import { ref, computed, nextTick } from 'vue'
import { inSlideShow, activeSlideInFocus, activeSlideElements } from './slide'
import { guessTextColorFromBackground } from '../utils/color'

const currentDataIndex = ref(null)
const currentFocusedIndex = ref(null)
const currentPairedDataIndex = ref(null)

const activeElement = computed(() => {
	if (currentDataIndex.value !== null) {
		return activeSlideElements.value[currentDataIndex.value]
	} else if (currentFocusedIndex.value !== null) {
		return activeSlideElements.value[currentFocusedIndex.value]
	}
})

const setActiveElement = (index, inFocus = false) => {
	if (inSlideShow.value) return

	if (activeElement.value && currentFocusedIndex.value) {
		activeElement.value.content = document.querySelector(
			`[data-index="${currentFocusedIndex.value}"]`,
		).innerText
	}
	if (inFocus) {
		currentFocusedIndex.value = index
		currentDataIndex.value = null
	} else {
		currentDataIndex.value = index
		currentFocusedIndex.value = null
	}
	activeSlideInFocus.value = false
}

const addTextElement = () => {
	const lastTextElement = activeSlideElements.value
		.reverse()
		.find((element) => element.type == 'text')

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
	activeSlideElements.value.push(element)
	nextTick(() => setActiveElement(activeSlideElements.value.length - 1))
}

const addMediaElement = (file, type) => {
	let element = {
		width: 300,
		left: 200,
		top: 75,
		opacity: 100,
		type: type,
		src: file.file_url,
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
	activeSlideElements.value.push(element)
	nextTick(() => setActiveElement(element))
}

const duplicateElement = (e) => {
	e.preventDefault()
	let newElement = JSON.parse(JSON.stringify(activeElement.value))
	newElement.top += 40
	newElement.left += 40
	activeSlideElements.value.push(newElement)
	nextTick(() => (currentDataIndex.value = activeSlideElements.value.indexOf(newElement)))
}

const deleteElement = (e) => {
	activeSlideElements.value.splice(currentDataIndex.value, 1)
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
