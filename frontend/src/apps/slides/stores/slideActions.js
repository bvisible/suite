import { nextTick } from 'vue'
import { call } from 'frappe-ui'
import html2canvas from 'html2canvas'
import {
	activeSlideElements,
	activeSlideIndex,
	currentTransitionSlide,
	applyReverseTransition,
	inSlideShow,
	name,
	presentation,
	slideTransition,
	slideTransitionDuration,
} from './slide'
import { resetFocus } from './element'

const updateSlideThumbnail = (index) => {
	if (inSlideShow.value) return
	const slideRef = document.querySelector('.slide')
	html2canvas(slideRef).then((canvas) => {
		let img = canvas.toDataURL('image/png')
		presentation.data.slides[index].thumbnail = img
	})
}

const updateSlideState = () => {
	let currentSlide = presentation.data.slides[activeSlideIndex.value]
	currentSlide.elements = JSON.stringify(activeSlideElements.value, null, 2)
	currentSlide.transition = slideTransition.value
	currentSlide.transition_duration = slideTransitionDuration.value
}

const triggerTransition = (index) => {
	currentTransitionSlide.value = index
	applyReverseTransition.value = index < activeSlideIndex.value
}

const loadSlide = (index) => {
	const { transition, transition_duration, elements } = presentation.data.slides[index]

	slideTransition.value = transition
	slideTransitionDuration.value = transition_duration
	activeSlideElements.value = elements ? JSON.parse(elements) : []
}

const changeSlide = (index) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	resetFocus()
	updateSlideState()
	triggerTransition(index)
	nextTick(() => {
		updateSlideThumbnail(activeSlideIndex.value)
		activeSlideIndex.value = index
		loadSlide(activeSlideIndex.value)
	})
}

const saveChanges = async () => {
	if (!presentation.data) return
	updateSlideState()
	await call('frappe.client.save', {
		doc: presentation.data,
	})
	await presentation.reload()
}

const insertSlide = async (index) => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.insert_slide', {
		name: name.value,
		index: index,
	})
	await presentation.reload()
	changeSlide(index + 1)
}

const deleteSlide = async () => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.delete_slide', {
		name: name.value,
		index: activeSlideIndex.value,
	})
	await presentation.reload()
	changeSlide(activeSlideIndex.value - 1)
}

const duplicateSlide = async (e) => {
	e.preventDefault()
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.duplicate_slide', {
		name: name.value,
		index: activeSlideIndex.value,
	})
	await presentation.reload()
	changeSlide(activeSlideIndex.value + 1)
}

export { changeSlide, saveChanges, insertSlide, deleteSlide, duplicateSlide }
