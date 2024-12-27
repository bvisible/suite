import { createResource } from 'frappe-ui'
import { ref } from 'vue'

const activePresentation = ref(null)

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

export { presentationList, activePresentation }
