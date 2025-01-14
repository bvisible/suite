import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'
import { isEqual } from 'lodash'
import { changeSlide } from './slideActions'

const name = ref('')
const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: name.value }),
})

const slideIndex = ref(0)

const slideFocus = ref(false)
const inSlideShow = ref(false)
const applyReverseTransition = ref(false)

const slide = ref({
	background: '#ffffff',
	elements: [],
	transition: null,
	transitionDuration: 0,
})

const position = ref(null)
const dimensions = ref(null)

const slideDirty = computed(() => {
	if (!presentation.data) return false
	const currentSlide = presentation.data.slides[slideIndex.value]
	const data = {
		elements: JSON.parse(currentSlide.elements),
		transition: currentSlide.transition,
		transition_duration: currentSlide.transition_duration,
	}
	const updatedData = {
		elements: slide.value.elements,
		transition: slide.value.transition,
		transition_duration: slide.value.transitionDuration,
	}
	return !isEqual(data, updatedData)
})

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
	name,
	presentation,
	slideIndex,
	slideFocus,
	slideDirty,
	inSlideShow,
	applyReverseTransition,
	slide,
	position,
	dimensions,
	startSlideShow,
}
