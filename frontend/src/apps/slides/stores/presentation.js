import { ref, watch } from 'vue'
import { createResource, call, createDocumentResource } from 'frappe-ui'
import { isEqual } from 'lodash'

import { slides, getSlideThumbnail, currentSlide } from './slide'

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
			}
		},
		onSuccess(doc) {
			slides.value = JSON.parse(JSON.stringify(doc.slides || []))
		},
	})
}

const compareSlideState = (originalState, slideState) => {
	const keysToCompare = ['name', 'background', 'transition', 'transition_duration']

	for (const key of keysToCompare) {
		if (slideState[key] != originalState[key]) return true
	}

	const currElements = parseElements(slideState.elements)
	const origElements = parseElements(originalState.elements)

	if (!isEqual(currElements, origElements)) return true
}

const hasStateChanged = (original, current) => {
	if (original.length != current.length) return true

	for (let i = 0; i < current.length; i++) {
		return compareSlideState(original[i], current[i])
	}

	return false
}

const savePresentationDoc = async () => {
	const thumbnail = await getSlideThumbnail()
	currentSlide.value.thumbnail = thumbnail

	const presentationResource = getPresentationResource(presentationId.value)

	const newSlides = slides.value.map((slide) => ({
		...slide,
		elements: JSON.stringify(slide.elements, null, 2),
	}))

	await presentationResource.setValue.submit({
		slides: newSlides,
	})

	await presentationResource.reload()

	return presentationResource.doc
}

const layoutResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_layouts',
	method: 'GET',
	auto: false,
	transform: (data) => {
		for (const slide of data || []) {
			slide.elements = parseElements(slide.elements)
		}
	},
	makeParams: ({ theme }) => {
		return {
			theme: theme,
		}
	},
})

export {
	presentationId,
	inSlideShow,
	applyReverseTransition,
	createPresentationResource,
	updatePresentationTitle,
	getPresentationResource,
	hasStateChanged,
	savePresentationDoc,
	layoutResource,
}
