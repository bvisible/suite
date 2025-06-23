import { ref, watch } from 'vue'
import { createResource, call } from 'frappe-ui'
import { loadSlide } from './slide'

const presentationId = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: presentationId.value }),
})

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

const loadPresentation = async (id) => {
	presentationId.value = id
	await presentation.fetch()
	loadSlide()
}

const createPresentationResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.create_presentation',
	method: 'POST',
	makeParams: (args) => {
		return {
			title: args.title,
			duplicate_from: args.duplicateFrom,
		}
	},
})

export {
	presentationId,
	presentation,
	inSlideShow,
	applyReverseTransition,
	loadPresentation,
	createPresentationResource,
}
