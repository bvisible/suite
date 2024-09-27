import { ref } from 'vue'
import { createResource } from 'frappe-ui'

const activeElement = ref(null)

const name = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: name.value }),
})

const activeSlideIndex = ref(1)

const activeSlideElements = ref([])

const inSlideShow = ref(false)

export { name, presentation, activeSlideIndex, activeElement, activeSlideElements, inSlideShow }
