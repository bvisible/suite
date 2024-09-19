import { computed, ref } from 'vue'
import { createResource } from 'frappe-ui'

const activeElement = ref(null)

const name = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: name.value }),
})

const activeSlideIndex = ref(1)

const activeSlide = computed(() => {
	return presentation.data.slides[activeSlideIndex.value - 1]
})

const activeSlideElements = ref([])

export { name, presentation, activeSlideIndex, activeSlide, activeElement, activeSlideElements }
