import { ref } from 'vue'
import { createResource } from 'frappe-ui'

import { changeSlide } from './slide'

const presentationId = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: presentationId.value }),
})

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

export { presentationId, presentation, presentationList, inSlideShow, applyReverseTransition }
