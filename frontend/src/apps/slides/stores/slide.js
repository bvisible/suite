import { ref } from 'vue'
import { createResource } from 'frappe-ui'

const name = ref('')
const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: name.value }),
})

const activeSlideIndex = ref(0)
const activeSlideInFocus = ref(false)
const activeSlideElements = ref([])

const inSlideShow = ref(false)
const currentTransitionSlide = ref(0)
const applyReverseTransition = ref(false)

const slideTransition = ref(null)
const slideTransitionDuration = ref(0)

const position = ref(null)
const dimensions = ref(null)

export {
	name,
	presentation,
	activeSlideIndex,
	activeSlideInFocus,
	activeSlideElements,
	inSlideShow,
	position,
	dimensions,
	currentTransitionSlide,
	applyReverseTransition,
	slideTransition,
	slideTransitionDuration,
}
