import { slides, slideIndex, currentSlide } from '@/stores/slide'
import { isElementInSlide } from '@/stores/element'
import { generateUniqueId } from '@/utils/helpers'

const canCreateTextConnection = (currentContent, nextContent) => {
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

const canCreateMediaConnection = (currentSrc, nextSrc) => {
	return currentSrc == nextSrc
}

const canCreateConnection = (currElement, potentialConnectionElement) => {
	if (currElement.type == 'text') {
		return canCreateTextConnection(currElement.content, potentialConnectionElement.content)
	}
	return canCreateMediaConnection(currElement.src, potentialConnectionElement.src)
}

const getReferenceElement = (currElement, slide) => {
	for (const element of slide.elements) {
		if (element.type != currElement.type) continue

		if (isElementInSlide(slideIndex.value, element.id)) continue

		if (canCreateConnection(currElement, element)) {
			return element
		}
	}
}

const getReferenceIdFromSlide = (candidateSlide, element) => {
	if (!candidateSlide) return null

	// find reference element in candidate slide
	const refElement = getReferenceElement(element, candidateSlide)
	// if found copy its id so that it does not re-render during transition
	return refElement?.id
}

const getUpdatedIdAfterConnections = (element) => {
	const prevSlide = slides.value[slideIndex.value - 1]
	const nextSlide = slides.value[slideIndex.value + 1]

	let id = getReferenceIdFromSlide(prevSlide, element)

	if (!id && currentSlide.value?.transition === 'Magic Move') {
		id = getReferenceIdFromSlide(nextSlide, element)
	}

	return id || element.id || generateUniqueId()
}

const createConnectionsForMagicMove = (index) => {
	// adding magic move to last slide changes nothing
	if (index == slides.value.length - 1) return

	const currentSlide = slides.value[index]
	const nextSlide = slides.value[index + 1]

	currentSlide.elements.forEach((currElement) => {
		const refElement = getReferenceElement(currElement, nextSlide)
		if (refElement) {
			const id = refElement.id
			currElement.id = id
			updateIdsAcrossSlides(slideIndex.value, currElement, id, false)
		}
	})
}

const updateIdsAcrossSlides = (fromSlideIndex, element, newId, isForward) => {
	let i = isForward ? fromSlideIndex + 1 : fromSlideIndex - 1

	while (i >= 0 && i < slides.value.length) {
		const slide = slides.value[i]
		const transition = isForward ? slides.value[i - 1]?.transition : slide.transition
		const hasTransition = transition === 'Magic Move'

		if (!hasTransition) break

		const refElement = getReferenceElement(element, slide)
		if (refElement) {
			refElement.id = newId
		}

		i += isForward ? 1 : -1
	}
}

const isAffectedByMagicMove = (slideIndex) => {
	const prevSlide = slides.value[slideIndex - 1]
	const currentSlide = slides.value[slideIndex]

	return prevSlide?.transition === 'Magic Move' || currentSlide?.transition === 'Magic Move'
}

const updateElementId = (element) => {
	const needsUpdate = isAffectedByMagicMove(slideIndex.value)
	if (!needsUpdate) return

	const id = getUpdatedIdAfterConnections(element)
	element.id = id
	updateIdsAcrossSlides(slideIndex.value, element, id, true)
}

export { createConnectionsForMagicMove, updateElementId }
