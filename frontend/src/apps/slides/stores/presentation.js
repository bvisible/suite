import { ref, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { loadSlide } from './slide'

const presentationId = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: presentationId.value }),
})

const inSlideShow = ref(false)

const applyReverseTransition = ref(false)

watch(
	() => presentationId.value,
	async () => {
		await presentation.fetch()
		loadSlide()
	},
)

export { presentationId, presentation, inSlideShow, applyReverseTransition }
