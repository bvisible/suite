import { ref, nextTick } from 'vue'
import { createResource, call } from 'frappe-ui'
import html2canvas from 'html2canvas'

const currentDataIndex = ref(null)

const currentFocusedIndex = ref(null)

const currentPairedDataIndex = ref(null)

const activeElement = ref(null)

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

const setActiveElement = (element, inFocus = false) => {
	if (inSlideShow.value) return

	if (activeElement.value && currentFocusedIndex.value) {
		activeElement.value.content = document.querySelector(
			`[data-index="${currentFocusedIndex.value}"]`,
		).innerText
	}

	activeElement.value = element
	const index = activeSlideElements.value.indexOf(element)
	if (inFocus) {
		currentFocusedIndex.value = index
		currentDataIndex.value = null
	} else {
		currentDataIndex.value = index
		currentFocusedIndex.value = null
	}
}

const updateSlideThumbnail = (slideDiv, index) => {
	if (!slideDiv) return
	html2canvas(slideDiv).then((canvas) => {
		let img = canvas.toDataURL('image/png')
		presentation.data.slides[index].thumbnail = img
	})
}

const changeSlide = (index) => {
	if (index < 0 || index >= presentation.data.slides.length) return
	presentation.data.slides[activeSlideIndex.value].elements = JSON.stringify(
		activeSlideElements.value,
	)
	if (activeElement.value?.type != 'slide') activeElement.value = null
	currentDataIndex.value = null
	currentFocusedIndex.value = null
	currentPairedDataIndex.value = null
	currentTransitionSlide.value = index
	nextTick(() => {
		if (!inSlideShow.value) {
			let slideRef = document.querySelector('.slide')
			if (slideRef) {
				updateSlideThumbnail(slideRef, activeSlideIndex.value)
			}
		}
		activeSlideIndex.value = index
		if (presentation.data.slides[activeSlideIndex.value].elements)
			activeSlideElements.value = JSON.parse(
				presentation.data.slides[activeSlideIndex.value].elements,
			)
		else activeSlideElements.value = []
	})
}

const saveChanges = async () => {
	if (!presentation.data) return
	presentation.data.slides[activeSlideIndex.value].elements = JSON.stringify(
		activeSlideElements.value,
		null,
		2,
	)
	await call('frappe.client.save', {
		doc: presentation.data,
	})
	await presentation.reload()
}

const insertSlide = async (index) => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.insert_slide', {
		name: name.value,
		index: index,
	})
	await presentation.reload()
}

const deleteSlide = async () => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.delete_slide', {
		name: name.value,
		index: activeSlideIndex.value,
	})
	await presentation.reload()
}

const duplicateSlide = async () => {
	await saveChanges()
	await call('slides.slides.doctype.presentation.presentation.duplicate_slide', {
		name: name.value,
		index: activeSlideIndex.value,
	})
	await presentation.reload()
}

const currentTransitionSlide = ref(0)

export {
	currentDataIndex,
	currentFocusedIndex,
	currentPairedDataIndex,
	name,
	presentation,
	activeSlideIndex,
	activeElement,
	activeSlideElements,
	inSlideShow,
	position,
	dimensions,
	currentTransitionSlide,
	setActiveElement,
	changeSlide,
	insertSlide,
	deleteSlide,
	duplicateSlide,
	saveChanges,
}
