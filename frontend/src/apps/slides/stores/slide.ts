import { ref, computed } from 'vue'
import { createResource } from 'frappe-ui'

const currentDataIndex = ref(null)

const currentPairedDataIndex = computed(() => {
	if (!activeElement.value) return
	let i = null
	activeSlideElements.value.forEach((element, index) => {
		if (index == currentDataIndex.value) return
		let diffLeft = Math.abs(element.left - activeElement.value.left)
		let diffRight = Math.abs(
			element.left + element.width - activeElement.value.left - activeElement.value.width,
		)
		if (diffLeft < 5 || diffRight < 5) i = index
	})
	return i
})

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
}
