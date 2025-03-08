import { ref } from 'vue'
import { createResource } from 'frappe-ui'

const presentationId = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: presentationId.value }),
})

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

export { presentationId, presentation, inSlideShow, applyReverseTransition }
