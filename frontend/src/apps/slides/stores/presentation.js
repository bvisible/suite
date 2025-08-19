import { ref, watch } from 'vue'
import { watchIgnorable, useManualRefHistory } from '@vueuse/core'
import { createResource, call, createDocumentResource } from 'frappe-ui'
import { isEqual } from 'lodash'

import { slides, slideIndex } from './slide'
import { activeElementIds } from '@/stores/element'

import { activeEditor } from '@/composables/useTextEditor'

const presentationDoc = ref()

const presentationId = ref('')

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

const createPresentationResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.create_presentation',
	method: 'POST',
	makeParams: (args) => {
		return {
			title: args.title,
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

const parseElements = (value) => {
	if (!value) return []
	if (typeof value === 'string') {
		try {
			return JSON.parse(value)
		} catch {
			return []
		}
	}
	return Array.isArray(value) ? value : []
}

const getPresentationResource = (name) => {
	return createDocumentResource({
		doctype: 'Presentation',
		name: name,
		auto: false,
		transform(doc) {
			for (const slide of doc.slides || []) {
				slide.elements = parseElements(slide.elements)
				slide.transitionDuration = slide.transition_duration
				// remove the transition_duration field to avoid confusion
				delete slide.transition_duration
			}
		},
		onSuccess(doc) {
			slides.value = JSON.parse(JSON.stringify(doc.slides || []))
		},
	})
}

const hasSlideChanged = (originalState, slideState) => {
	const keysToCompare = ['background', 'transition', 'transitionDuration']

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

const savePresentationDoc = async () => {
	const newSlides = slides.value.map((slide) => ({
		...slide,
		elements: JSON.stringify(slide.elements, null, 2),
		transition_duration: slide.transitionDuration,
	}))

	await presentationResource.value.setValue.submit({
		slides: newSlides,
	})

	presentationDoc.value = presentationResource.value.doc
}

const layoutResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_layouts',
	method: 'GET',
	auto: false,
	transform: (data) => {
		for (const slide of data || []) {
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

const initPresentationDoc = async (id) => {
	presentationId.value = id
	presentationResource.value = getPresentationResource(id)
	await presentationResource.value.get.fetch()
	return presentationResource.value.doc
}

let historyControl = null

const historyState = ref({
	elementIds: '',
	activeSlide: 0,
	slides: [],
})

const deepClone = (obj) => JSON.parse(JSON.stringify(obj))

const updateHistoryState = (slides, activeSlide, elementIds) => {
	const slidesClone = [...slides].map((slide) => {
		return {
			...slide,
			elements: slide.elements.map((el) => deepClone(el)),
		}
	})

	historyState.value = {
		elementIds: elementIds,
		activeSlide: Number(activeSlide),
		slides: slidesClone,
	}
}

const { ignoreUpdates } = watchIgnorable(
	() => slides.value,
	(newVal) => {
		if (!newVal.length) return

		updateHistoryState(newVal, slideIndex.value, activeElementIds.value)

		historyControl.commit()
	},
	{ deep: true },
)

const initHistory = () => {
	historyControl = useManualRefHistory(historyState, {
		capacity: 25,
		clone: true,
		deep: true,
	})
}

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
}
