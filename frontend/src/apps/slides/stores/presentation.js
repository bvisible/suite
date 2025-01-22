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

const startSlideShow = async () => {
	if (!presentation.data) await presentation.reload()
	await changeSlide(0)
	const elem = document.querySelector('.slideContainer')

	if (elem.requestFullscreen) {
		elem.requestFullscreen()
	} else if (elem.webkitRequestFullscreen) {
		elem.webkitRequestFullscreen()
	} else if (elem.msRequestFullscreen) {
		elem.msRequestFullscreen()
	}
}

export {
	presentationId,
	presentation,
	presentationList,
	inSlideShow,
	applyReverseTransition,
	startSlideShow,
}
