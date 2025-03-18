import { ref, computed, nextTick, reactive } from 'vue'
import { call } from 'frappe-ui'

import { presentationId, presentation, applyReverseTransition, inSlideShow } from './presentation'
import { activeElementIds, activePosition, resetFocus } from './element'

import { isEqual } from 'lodash'
import html2canvas from 'html2canvas'

const slideIndex = ref(0)

const slide = ref({
	background: '#ffffff',
	elements: [],
	transition: null,
	transitionDuration: 0,
})

const getSavedData = () => {
	const currentSlide = presentation.data?.slides[slideIndex.value]
	if (!currentSlide) return {}

	return {
		elements: JSON.parse(currentSlide.elements || '[]'),
		transition: currentSlide.transition,
		transition_duration: currentSlide.transition_duration,
		background: currentSlide.background,
	}
}

const getCurrentData = () => {
	const updatedData = {
		elements: slide.value.elements,
		transition: slide.value.transition,
		transition_duration: slide.value.transitionDuration,
		background: slide.value.background,
	}

	if (activePosition.value) {
		const dx = activePosition.value.left - slideDimensions.left
		const dy = activePosition.value.top - slideDimensions.top

		const elementsCopy = JSON.parse(JSON.stringify(slide.value.elements))
		elementsCopy.forEach((element, index) => {
			if (activeElementIds.value.includes(index)) {
				element.left = element.left + dx
				element.top = element.top + dy
			}
		})

		updatedData.elements = elementsCopy
	}

	return updatedData
}

const slideDirty = computed(() => {
	const data = getSavedData()
	const updatedData = getCurrentData()

	return !isEqual(data, updatedData)
})

const getSlideThumbnail = async () => {
	const slideRef = document.querySelector('.slide')
	const scale = slideRef.getBoundingClientRect().width / 960
	if (scale !== 1) {
		return slide.value.thumbnail
	}
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

const loadSlide = () => {
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

const changeSlide = async (index, updateCurrent = true) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	resetFocus()
	applyReverseTransition.value = index < slideIndex.value

	nextTick(async () => {
		if (updateCurrent) await updateSlideState()
		slideIndex.value = index
		loadSlide()
	})
}

const saving = ref(false)

const saveChanges = async () => {
	if (!presentation.data || !slideDirty.value) return
	slide.value.elements = slide.value.elements.map((element, index) => {
		let rect = document.querySelector(`[data-index="${index}"]`).getBoundingClientRect()
		element.width = rect.width / slideDimensions.scale
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
	const newIndex =
		slideIndex.value === presentation.data.slides.length
			? slideIndex.value - 1
			: slideIndex.value
	await changeSlide(newIndex, false)
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

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	resetFocus()
}

const slideDimensions = reactive({})

export {
	slideIndex,
	slideDirty,
	saving,
	slide,
	slideDimensions,
	getSlideThumbnail,
	loadSlide,
	saveChanges,
	changeSlide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
	selectSlide,
}
