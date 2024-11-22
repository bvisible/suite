import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'

const currentDataIndex = ref(null)

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

const pairElement = computed(() => {
	if (!activeElement.value) return null
	let element = null
	activeSlideElements.value.forEach((el, index) => {
		if (index == currentDataIndex.value) return
		let diffLeft = Math.abs(el.left - activeElement.value.left)
		let diffRight = Math.abs(
			el.left + el.width - activeElement.value.left - activeElement.value.width,
		)
		if (diffLeft < 5 || diffRight < 5) {
			element = el
		}
	})
	return element
})

export {
	currentDataIndex,
	name,
	presentation,
	activeSlideIndex,
	activeElement,
	pairElement,
	activeSlideElements,
	inSlideShow,
	focusedElement,
}
