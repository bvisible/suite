import { ref, computed, nextTick } from 'vue'
import { call } from 'frappe-ui'

import { presentationId, presentation, inSlideShow, applyReverseTransition } from './presentation'
import { activeElementIds, resetFocus } from './element'

import { isEqual } from 'lodash'
import html2canvas from 'html2canvas'

const slideRect = ref(null)

const slideIndex = ref(0)
const slideFocus = ref(false)

const slide = ref({
	background: '#ffffff',
	elements: [],
	transition: null,
	transitionDuration: 0,
})

const slideDirty = computed(() => {
	if (!presentation.data) return false
	const currentSlide = presentation.data.slides[slideIndex.value]
	const data = {
		elements: JSON.parse(currentSlide.elements || '[]'),
		transition: currentSlide.transition,
		transition_duration: currentSlide.transition_duration,
		background: currentSlide.background,
	}
	const updatedData = {
		elements: slide.value.elements,
		transition: slide.value.transition,
		transition_duration: slide.value.transitionDuration,
		background: slide.value.background,
	}
	return !isEqual(data, updatedData)
})

const getSlideThumbnail = async () => {
	if (inSlideShow.value) return
	const slideRef = document.querySelector('.slide')
	const canvas = await html2canvas(slideRef)
	return canvas.toDataURL('image/png')
}

const updateSlideState = async () => {
	slide.value.thumbnail = await getSlideThumbnail()
	const { elements, transition, transitionDuration, background, thumbnail } = slide.value
	presentation.data.slides[slideIndex.value] = {
		...presentation.data.slides[slideIndex.value],
		background,
		transition,
		thumbnail,
		elements: JSON.stringify(elements, null, 2),
		transition_duration: transitionDuration,
	}
}

const loadSlide = (index) => {
	const { background, transition, transition_duration, elements, thumbnail } =
		presentation.data.slides[slideIndex.value]

	slide.value = {
		background,
		transition,
		thumbnail,
		transitionDuration: transition_duration,
		elements: elements ? JSON.parse(elements) : [],
	}
}

const changeSlide = async (index) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	resetFocus()
	applyReverseTransition.value = index < slideIndex.value
	await nextTick(async () => {
		await updateSlideState()
		slideIndex.value = index
		loadSlide(slideIndex.value)
	})
}

const saving = ref(false)

const saveChanges = async () => {
	if (!presentation.data || !slideDirty.value) return
	slide.value.elements = slide.value.elements.map((element, index) => {
		let div = document.querySelector(`[data-index="${index}"]`)
		element.width = div.offsetWidth
		element.height = div.offsetHeight
		return element
	})
	saving.value = true
	resetFocus()
	await nextTick(async () => {
		await updateSlideState()
	})
	await call('frappe.client.save', {
		doc: presentation.data,
	})
	await presentation.reload()
	saving.value = false
}

const insertSlide = async (index) => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.insert_slide', {
		name: presentationId.value,
		index: index,
	})
	await presentation.reload()
	await changeSlide(index)
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

export {
	slideIndex,
	slideDirty,
	saving,
	slideFocus,
	slide,
	slideRect,
	getSlideThumbnail,
	loadSlide,
	saveChanges,
	changeSlide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
}
