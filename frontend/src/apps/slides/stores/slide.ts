import { ref } from 'vue'
import { createResource } from 'frappe-ui'

const currentDataIndex = ref(null)

const currentPairedDataIndex = ref(null)

const activeElement = ref(null)

const focusedElement = ref(null)

const name = ref('')

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: name.value }),
})

const activeSlideIndex = ref(0)

const activeSlideElements = ref([])

const inSlideShow = ref(false)

const position = ref(null)
const dimensions = ref(null)

export {
	currentDataIndex,
	currentPairedDataIndex,
	name,
	presentation,
	activeSlideIndex,
	activeElement,
	activeSlideElements,
	inSlideShow,
	focusedElement,
	position,
	dimensions,
}
