import { ref, nextTick, computed } from 'vue'
import { createResource } from 'frappe-ui'

const currentDataIndex = ref(null)
const currentFocusedIndex = ref(null)
const currentPairedDataIndex = ref(null)

const activeElement = computed(() => {
	if (currentDataIndex.value !== null) {
		return activeSlideElements.value[currentDataIndex.value]
	} else if (currentFocusedIndex.value !== null) {
		return activeSlideElements.value[currentFocusedIndex.value]
	}
})

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

const position = ref(null)
const dimensions = ref(null)

const setActiveElement = (element, inFocus = false) => {
	if (inSlideShow.value) return

	if (activeElement.value && currentFocusedIndex.value) {
		activeElement.value.content = document.querySelector(
			`[data-index="${currentFocusedIndex.value}"]`,
		).innerText
	}
	const index = activeSlideElements.value.indexOf(element)
	if (inFocus) {
		currentFocusedIndex.value = index
		currentDataIndex.value = null
	} else {
		currentDataIndex.value = index
		currentFocusedIndex.value = null
	}
	activeSlideInFocus.value = false
}

const resetFocus = () => {
	currentDataIndex.value = null
	currentFocusedIndex.value = null
	currentPairedDataIndex.value = null
}

export {
	currentDataIndex,
	currentFocusedIndex,
	currentPairedDataIndex,
	name,
	presentation,
	activeSlideIndex,
	activeSlideInFocus,
	activeElement,
	activeSlideElements,
	inSlideShow,
	position,
	dimensions,
	currentTransitionSlide,
	applyReverseTransition,
	setActiveElement,
	resetFocus,
}
