import { slides, slideIndex, currentSlide } from '@/stores/slide'
import { generateUniqueId } from '@/utils/helpers'

const compareTextContentForHTML = (currentContent, nextContent) => {
	const parser = new DOMParser()

	const doc = parser.parseFromString(currentContent, 'text/html')
	const nextDoc = parser.parseFromString(nextContent, 'text/html')

	const currentBlocks = doc.body.children
	const nextBlocks = nextDoc.body.children

	if (currentBlocks.length != nextBlocks.length) return false

	for (let i = 0; i < currentBlocks.length; i++) {
		// within each block, compare text content only (ignore styles and tags)
		if (currentBlocks[i].textContent != nextBlocks[i].textContent) {
			return false
		}
	}

	return true
}

const getReferenceElement = (nextElement, slide) => {
	for (const element of slide.elements) {
		if (element.type != nextElement.type) continue

		const hasSameText =
			element.type == 'text' &&
			compareTextContentForHTML(element.content, nextElement.content)
		const hasSameSrc = element.type != 'text' && element.src == nextElement.src

		if (hasSameText || hasSameSrc) {
			return element
		}
	}
}

const getUpdatedIdAfterConnections = (element, currentText) => {
	const prevSlide = slides.value[slideIndex.value - 1]
	const nextSlide = slides.value[slideIndex.value + 1]

	let candidateSlide = null
	if (prevSlide?.transition === 'Magic Move') {
		// if transition begins on previous slide -
		// check if any element in current slide refers to element from previous slide
		candidateSlide = prevSlide
	} else if (currentSlide.value?.transition === 'Magic Move' && nextSlide) {
		// if transition begins on current slide -
		// check if any element in next slide refers to this element
		candidateSlide = nextSlide
	}

	if (candidateSlide) {
		// find reference element in candidate slide
		const refElement = getReferenceElement(element, candidateSlide)
		// if found copy its id so that it does not re-render during transition
		if (refElement) return refElement.id
	}

	return generateUniqueId()
}

const createConnectionsForMagicMove = () => {
	// adding magic move to last slide changes nothing
	if (slideIndex.value == slides.value.length - 1) return

	const nextSlide = slides.value[slideIndex.value + 1]
	nextSlide.elements.forEach((nextElement) => {
		const refElement = getReferenceElement(nextElement, currentSlide.value)

		if (refElement) {
			// update current element id to match reference from previous slide
			nextElement.id = refElement.id
		}
	})
}

export { createConnectionsForMagicMove, getUpdatedIdAfterConnections }
