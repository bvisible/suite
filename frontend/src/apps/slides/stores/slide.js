import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'
import { isEqual } from 'lodash'

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

const isDirty = computed(() => {
	if (!presentation.data) return false
	const oldData = JSON.parse(presentation.data.slides[activeSlideIndex.value].elements)
	const newData = activeSlideElements.value
	return !isEqual(oldData, newData)
})

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
	isDirty,
}
