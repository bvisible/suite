import { ref, watch } from 'vue'
import { createResource, call } from 'frappe-ui'

const presentationId = ref('')

const slides = ref([])

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	cache: 'presentation',
	makeParams: () => ({ name: presentationId.value }),
	onSuccess: (data) => {
		const slidesCopy = JSON.parse(JSON.stringify(data.slides))
		slides.value = slidesCopy.map((slide) => ({
			...slide,
			elements: JSON.parse(slide.elements || '[]'),
		}))
	},
})

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

export {
	presentationId,
	presentation,
	inSlideShow,
	applyReverseTransition,
	createPresentationResource,
	updatePresentationTitle,
	slides,
}
