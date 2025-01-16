import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'
import { isEqual } from 'lodash'
import { presentation } from './presentation'

const slideIndex = ref(0)
const slideFocus = ref(false)

const slide = ref({
	background: '#ffffff',
	elements: [],
	transition: null,
	transitionDuration: 0,
})

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

export { slideIndex, slideFocus, slideDirty, slide }
