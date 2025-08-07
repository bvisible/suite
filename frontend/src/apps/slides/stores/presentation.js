import { ref, watch, computed } from 'vue'
import { createResource, call } from 'frappe-ui'
import { useDebouncedRefHistory } from '@vueuse/core'

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

export {
	presentationId,
	inSlideShow,
	applyReverseTransition,
	createPresentationResource,
	updatePresentationTitle,
}
