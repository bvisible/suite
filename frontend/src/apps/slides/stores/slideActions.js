import { nextTick } from 'vue'
import { call } from 'frappe-ui'
import html2canvas from 'html2canvas'
import {
	activeElement,
	activeSlideElements,
	activeSlideIndex,
	currentDataIndex,
	currentFocusedIndex,
	currentPairedDataIndex,
	currentTransitionSlide,
	applyReverseTransition,
	inSlideShow,
	name,
	presentation,
} from './slide'

const updateSlideThumbnail = (slideDiv, index) => {
	if (!slideDiv) return
	html2canvas(slideDiv).then((canvas) => {
		let img = canvas.toDataURL('image/png')
		presentation.data.slides[index].thumbnail = img
	})
}

const changeSlide = (index) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	presentation.data.slides[activeSlideIndex.value].elements = JSON.stringify(
		activeSlideElements.value,
	)
	if (activeElement.value?.type != 'slide') activeElement.value = null
	currentDataIndex.value = null
	currentFocusedIndex.value = null
	currentPairedDataIndex.value = null
	currentTransitionSlide.value = index
	applyReverseTransition.value = index < activeSlideIndex.value
	nextTick(() => {
		if (!inSlideShow.value) {
			let slideRef = document.querySelector('.slide')
			if (slideRef) {
				updateSlideThumbnail(slideRef, activeSlideIndex.value)
			}
		}
		activeSlideIndex.value = index
		if (presentation.data.slides[activeSlideIndex.value].elements)
			activeSlideElements.value = JSON.parse(
				presentation.data.slides[activeSlideIndex.value].elements,
			)
		else activeSlideElements.value = []
	})
}

const saveChanges = async () => {
	if (!presentation.data) return
	presentation.data.slides[activeSlideIndex.value].elements = JSON.stringify(
		activeSlideElements.value,
		null,
		2,
	)
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
}

const deleteSlide = async () => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.delete_slide', {
		name: name.value,
		index: activeSlideIndex.value,
	})
	await presentation.reload()
}

const duplicateSlide = async () => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.duplicate_slide', {
		name: name.value,
		index: activeSlideIndex.value,
	})
	await presentation.reload()
}

export { changeSlide, saveChanges, insertSlide, deleteSlide, duplicateSlide }
