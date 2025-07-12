import { ref, computed, nextTick, reactive } from 'vue'
import { call } from 'frappe-ui'

import { presentationId, presentation, inSlideShow } from './presentation'
import { activeElementIds } from './element'

import { isEqual } from 'lodash'
import html2canvas from 'html2canvas'

const slideIndex = ref(0)

const slide = ref({
	background: '#ffffff',
	elements: [],
	transition: null,
	transitionDuration: 0,
})

const selectionBounds = reactive({
	left: 0,
	top: 0,
	width: 0,
	height: 0,
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
	if (!slide.value) return {}
	return {
		elements: slide.value.elements,
		transition: slide.value.transition,
		transition_duration: slide.value.transitionDuration,
		background: slide.value.background,
	}
}

const isSlideDirty = () => {
	const data = getSavedData()
	const updatedData = getCurrentData()

	return !isEqual(data, updatedData)
}

const getThumbnailHtml = () => {
	const slideRef = document.querySelector('.slide')

	const clone = slideRef.cloneNode(true)

	clone.style.position = 'absolute'
	clone.style.left = '-9999px'
	clone.style.top = '0'
	clone.style.transform = 'scale(1)'

	clone.querySelectorAll('*').forEach((element) => {
		if (element.hasAttribute('data-index')) {
			element.style.position = 'absolute'
		}
	})

	return clone
}

const getSlideThumbnail = async () => {
	const thumbnailHtml = getThumbnailHtml()

	document.body.appendChild(thumbnailHtml)

	const canvas = await html2canvas(thumbnailHtml, {
		scale: window.devicePixelRatio,
	})

	document.body.removeChild(thumbnailHtml)

	return canvas.toDataURL('image/png')
}

const updateSlideState = async () => {
	const { elements, transition, transitionDuration, background } = slide.value
	presentation.data.slides[slideIndex.value] = {
		...presentation.data.slides[slideIndex.value],
		background,
		transition,
		elements: JSON.stringify(elements, null, 2),
		transition_duration: transitionDuration,
		thumbnail: await getSlideThumbnail(),
	}
}

const updateSlideThumbnail = async () => {
	if (!presentation.data || !slide.value) return

	const thumbnail = await getSlideThumbnail()
	slide.value.thumbnail = thumbnail
	presentation.data.slides[slideIndex.value].thumbnail = thumbnail
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
	const dirty = isSlideDirty()

	if (!presentation.data || !dirty) return

	// update presentation object with the latest slide data
	await updateSlideState()

	await call('frappe.client.save', {
		doc: presentation.data,
	})

	slide.value.thumbnail = presentation.data.slides[slideIndex.value].thumbnail

	await presentation.reload()
}

const slideBounds = reactive({})

const updateSelectionBounds = (newBounds) => {
	const roundedBounds = Object.fromEntries(
		Object.entries(newBounds).map(([key, value]) => [key, Math.round(value * 100) / 100]),
	)
	Object.assign(selectionBounds, roundedBounds)
}

const guideVisibilityMap = reactive({
	centerX: false,
	centerY: false,
	leftEdge: false,
	rightEdge: false,
	topEdge: false,
	bottomEdge: false,
})

export {
	slideIndex,
	slide,
	slideBounds,
	selectionBounds,
	guideVisibilityMap,
	loadSlide,
	updateSlideState,
	saveChanges,
	updateSelectionBounds,
	updateSlideThumbnail,
}
