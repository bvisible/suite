import { nextTick } from 'vue'
import { call } from 'frappe-ui'
import html2canvas from 'html2canvas'
import { presentationId, presentation } from './presentation'
import { slide, slideIndex, applyReverseTransition, inSlideShow, slideDirty } from './slide'
import { resetFocus } from './element'

const updateSlideThumbnail = async (index) => {
	if (inSlideShow.value) return
	const slideRef = document.querySelector('.slide')
	html2canvas(slideRef).then((canvas) => {
		presentation.data.slides[index].thumbnail = canvas.toDataURL('image/png')
	})
}

const updateSlideState = () => {
	const { elements, transition, transitionDuration, background } = slide.value
	let currentSlide = presentation.data.slides[slideIndex.value]

	currentSlide = {
		background,
		transition,
		elements: JSON.stringify(elements),
		transition_duration: transitionDuration,
	}
}

const loadSlide = (index) => {
	const { background, transition, transition_duration, elements } =
		presentation.data.slides[slideIndex.value]

	slide.value = {
		background,
		transition,
		transitionDuration: transition_duration,
		elements: elements ? JSON.parse(elements) : [],
	}
}

const changeSlide = async (index) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	resetFocus()
	updateSlideState()
	applyReverseTransition.value = index < slideIndex.value
	await nextTick(async () => {
		await updateSlideThumbnail(slideIndex.value)
		slideIndex.value = index
		loadSlide(slideIndex.value)
	})
}

const saveChanges = async () => {
	if (!presentation.data || !slideDirty.value) return
	updateSlideState()
	await call('frappe.client.save', {
		doc: presentation.data,
	})
	await presentation.reload()
}

const insertSlide = async (index) => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.insert_slide', {
		name: presentationId.value,
		index: index,
	})
	await presentation.reload()
	changeSlide(index + 1)
}

const deleteSlide = async () => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.delete_slide', {
		name: presentationId.value,
		index: slideIndex.value,
	})
	await presentation.reload()
	await changeSlide(slideIndex.value - 1)
}

const duplicateSlide = async (e) => {
	e.preventDefault()
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.duplicate_slide', {
		name: presentationId.value,
		index: slideIndex.value,
	})
	await presentation.reload()
	changeSlide(slideIndex.value + 1)
}

export { changeSlide, saveChanges, insertSlide, deleteSlide, duplicateSlide }
