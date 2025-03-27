import { ref, computed, nextTick, reactive } from 'vue'
import { call } from 'frappe-ui'

import { presentationId, presentation, inSlideShow } from './presentation'
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
		thumbnail: currentSlide.thumbnail,
	}
}

const getCurrentData = async () => {
	const updatedData = {
		elements: slide.value.elements,
		transition: slide.value.transition,
		transition_duration: slide.value.transitionDuration,
		background: slide.value.background,
		thumbnail: await getSlideThumbnail(),
	}

	if (activePosition.value) {
		const dx = activePosition.value.left - slideBounds.left
		const dy = activePosition.value.top - slideBounds.top

		const elementsCopy = JSON.parse(JSON.stringify(slide.value.elements))
		elementsCopy.forEach((element) => {
			if (activeElementIds.value.includes(element.id)) {
				element.left = element.left + dx
				element.top = element.top + dy
			}
		})

		updatedData.elements = elementsCopy
	}

	return updatedData
}

const isSlideDirty = async () => {
	const data = getSavedData()
	const updatedData = await getCurrentData()

	return !isEqual(data, updatedData)
}

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
	const { elements, transition, transitionDuration, background, thumbnail } = slide.value
	presentation.data.slides[slideIndex.value] = {
		...presentation.data.slides[slideIndex.value],
		background,
		transition,
		elements: JSON.stringify(elements, null, 2),
		transition_duration: transitionDuration,
		thumbnail: await getSlideThumbnail(),
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

const saveChanges = async () => {
	const dirty = await isSlideDirty()

	if (!presentation.data || !dirty) return

	// update presentation object with the latest slide data
	await updateSlideState()

	await call('frappe.client.save', {
		doc: presentation.data,
	})

	await presentation.reload()
}

const selectSlide = (e) => {
	e.preventDefault()
	e.stopPropagation()
	resetFocus()
}

const slideBounds = reactive({})

export { slideIndex, slide, slideBounds, loadSlide, updateSlideState, saveChanges, selectSlide }
