import { ref, reactive } from 'vue'
import { watchIgnorable, useManualRefHistory } from '@vueuse/core'
import { createResource, call, createDocumentResource } from 'frappe-ui'
import { isEqual } from 'lodash'

import { slides, slideIndex, currentSlide } from './slide'
import { activeElementIds, normalizeZIndices } from '@/stores/element'

import { cloneObj } from '@/utils/helpers'

const presentationDoc = ref()

const presentationId = ref('')

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

const createPresentationResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.create_presentation',
	method: 'POST',
	makeParams: (args) => {
		return {
			duplicate_from: args.duplicateFrom,
			theme: args.theme,
		}
	},
	transform: (response) => {
		return response.name
	},
})

const updatePresentationTitle = async (id, newTitle) => {
	return call('slides.slides.doctype.presentation.presentation.update_title', {
		name: id,
		title: newTitle,
	}).then((response) => {
		if (response) {
			return response
		} else {
			throw new Error('Failed to rename presentation')
		}
	})
}

const getElementDimensions = async (el) => {
	let width = 0,
		height = 0

	//render outside dom to get width
	const tempDiv = document.createElement('div')
	tempDiv.style.position = 'absolute'
	tempDiv.style.visibility = 'hidden'
	tempDiv.style.height = 'auto'
	tempDiv.style.width = 'auto'
	tempDiv.style.whiteSpace = 'pre'

	tempDiv.innerHTML = el.content || ''
	document.body.appendChild(tempDiv)

	await document.fonts.ready

	width = el.width || tempDiv.offsetWidth
	height = tempDiv.offsetHeight

	document.body.removeChild(tempDiv)

	return { width, height }
}

const transformElements = async (elements) => {
	const newEls = []

	for (const el of elements) {
		if ('transform' in el || el.type !== 'text') {
			newEls.push(el)
			continue
		}

		const { width, height } = await getElementDimensions(el)

		const newLeft = el.left + width / 2
		const newTop = el.top + height / 2

		newEls.push({
			...el,
			transform: 'translate(-50%, -50%)',
			transformOrigin: 'center center',
			left: newLeft,
			top: newTop,
		})
	}

	return newEls
}

const parseElements = (value) => {
	if (!value) return []

	let parsed = []
	if (Array.isArray(value)) {
		parsed = value
	} else if (typeof value === 'string') {
		try {
			parsed = JSON.parse(value)
		} catch {
			return []
		}
	}

	return normalizeZIndices(parsed)
}

const slidesLength = ref(0)

const getPresentationResource = (name) => {
	return createDocumentResource({
		doctype: 'Presentation',
		name: name,
		auto: false,
		transform(doc) {
			for (const slide of doc.slides || []) {
				slide.thumbnail = slide.thumbnail || ''
				slide.elements = parseElements(slide.elements)
				slide.transitionDuration = slide.transition_duration
				slide.fadeUnmatchedElements = slide.fade_unmatched_elements
				// remove the transition_duration field to avoid confusion
				delete slide.transition_duration
				delete slide.fade_unmatched_elements
			}
		},
		async onSuccess(doc) {
			slidesLength.value = doc.slides?.length || 0
			for (const slide of doc.slides || []) {
				slide.elements = await transformElements(slide.elements)
			}
			slides.value = JSON.parse(JSON.stringify(doc.slides || []))
			isPublicPresentation.value = Boolean(doc.is_public)
		},
	})
}

const getPublicPresentationResource = (name) => {
	return createResource({
		url: 'slides.slides.doctype.presentation.presentation.get_public_presentation',
		method: 'GET',
		auto: false,
		makeParams: () => {
			return { name: name }
		},
		transform(doc) {
			for (const slide of doc.slides || []) {
				slide.thumbnail = slide.thumbnail || ''
				slide.elements = parseElements(slide.elements)
				slide.transitionDuration = slide.transition_duration
				slide.fadeUnmatchedElements = slide.fade_unmatched_elements
				// remove the transition_duration field to avoid confusion
				delete slide.transition_duration
				delete slide.fade_unmatched_elements
			}
		},
		onSuccess(doc) {
			slidesLength.value = doc.slides?.length || 0
			slides.value = JSON.parse(JSON.stringify(doc.slides || []))
			isPublicPresentation.value = Boolean(doc.is_public)
		},
	})
}

const getCompositePresentationResource = (name) => {
	return createResource({
		url: 'slides.slides.doctype.presentation.presentation.get_composite_presentation',
		method: 'GET',
		auto: false,
		makeParams: () => {
			return { name: name }
		},
		transform(doc) {
			for (const slide of doc.slides || []) {
				slide.thumbnail = slide.thumbnail || ''
				slide.elements = parseElements(slide.elements)
				slide.transitionDuration = slide.transition_duration
				slide.fadeUnmatchedElements = slide.fade_unmatched_elements
				// remove the transition_duration field to avoid confusion
				delete slide.transition_duration
				delete slide.fade_unmatched_elements
			}
		},
		onSuccess(doc) {
			slidesLength.value = doc.slides?.length || 0
			slides.value = JSON.parse(JSON.stringify(doc.slides || []))
			isPublicPresentation.value = true
		},
	})
}

const hasSlideChanged = (originalState, slideState) => {
	const keysToCompare = [
		'background',
		'transition',
		'transitionDuration',
		'fadeUnmatchedElements',
	]

	for (const key of keysToCompare) {
		if (slideState[key] != originalState[key]) return true
	}

	if (slideState.name != '' && slideState.name != originalState.name) return true

	const currElements = parseElements(slideState.elements)
	const origElements = parseElements(originalState.elements)

	return !isEqual(currElements, origElements)
}

const hasStateChanged = (original, current) => {
	if (original.length != current.length) return true

	let hasChanged = false
	for (let i = 0; i < current.length; i++) {
		if (hasSlideChanged(original[i], current[i])) {
			hasChanged = true
			break
		}
	}

	return hasChanged
}

const updateNewlyAddedSlideUUIDs = () => {
	// for newly added slides, update their names from server response
	// required for correct jumping to slide during undo / redo operations
	ignoreUpdates(() => {
		slides.value.forEach((slide, idx) => {
			if (slide.name === '') {
				slide.name = presentationResource.value.doc.slides[idx]?.name
			}
		})
	})
}

const savePresentationDoc = async () => {
	const newSlides = slides.value.map((slide) => ({
		...slide,
		elements: JSON.stringify(slide.elements, null, 2),
		transition_duration: slide.transitionDuration,
		fade_unmatched_elements: slide.fadeUnmatchedElements,
	}))

	await presentationResource.value.setValue.submit({
		slides: newSlides,
	})

	presentationDoc.value = presentationResource.value.doc

	updateNewlyAddedSlideUUIDs()
}

const layoutResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_layouts',
	method: 'GET',
	auto: false,
	transform: (data) => {
		for (const slide of data.slides || []) {
			slide.thumbnail = slide.thumbnail || ''
			slide.elements = parseElements(slide.elements)
			slide.transitionDuration = slide.transition_duration
			// remove the transition_duration field to avoid confusion
			delete slide.transition_duration
		}
	},
	makeParams: ({ theme }) => {
		return {
			theme: theme,
		}
	},
})

const presentationResource = ref(null)

const initPresentationDoc = async (id, readonly = false) => {
	presentationId.value = id
	if (readonly) {
		presentationResource.value = getPublicPresentationResource(id)
		await presentationResource.value.fetch()
		if (presentationResource.value.data.is_composite) {
			presentationResource.value = getCompositePresentationResource(id)
			await presentationResource.value.fetch()
		}
		return presentationResource.value.data
	} else {
		presentationResource.value = getPresentationResource(id)
		await presentationResource.value.get.fetch()
		return presentationResource.value.doc
	}
}

let historyControl = null

const historyState = ref({
	elementIds: '',
	activeSlide: '',
	slides: [],
})

const historyMetadata = reactive({})

const updateHistoryState = (slides, activeSlide, elementIds) => {
	const slidesClone = [...slides].map((slide, idx) => {
		return {
			...slide,
			elements: slide.elements.map((el) => cloneObj(el)),
		}
	})

	historyState.value = {
		elementIds: elementIds,
		activeSlide: activeSlide,
		slides: slidesClone,
	}
}

const { ignoreUpdates } = watchIgnorable(
	() => slides.value,
	(newVal) => {
		if (!newVal.length) return
		commitToHistory(newVal)
	},
	{ deep: true },
)

const commitToHistory = (state) => {
	const activeSlide = currentSlide.value?.name
	const elementIds = activeElementIds.value

	updateHistoryState(state, activeSlide, elementIds)

	historyControl?.commit()
}

const initHistory = () => {
	historyState.value.activeSlide = currentSlide.value?.name
	historyControl = useManualRefHistory(historyState, {
		capacity: 25,
		clone: true,
		deep: true,
	})
}

const unsyncedPresentationRecord = ref({})

const isPublicPresentation = ref(false)

const readonlyMode = ref(false)

export {
	presentationId,
	inSlideShow,
	applyReverseTransition,
	createPresentationResource,
	updatePresentationTitle,
	getPresentationResource,
	hasStateChanged,
	savePresentationDoc,
	initPresentationDoc,
	layoutResource,
	presentationDoc,
	historyControl,
	historyState,
	initHistory,
	ignoreUpdates,
	unsyncedPresentationRecord,
	isPublicPresentation,
	readonlyMode,
	slidesLength,
	parseElements,
	historyMetadata,
}
