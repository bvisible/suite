import { createResource } from 'frappe-ui'
import { ref } from 'vue'

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

export { presentationId, presentation, presentationList }
