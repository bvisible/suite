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

const getElementId = (candidateSlide, element) => {
	if (!candidateSlide) return null

	// find reference element in candidate slide
	const refElement = getReferenceElement(element, candidateSlide)
	// if found copy its id so that it does not re-render during transition
	return refElement?.id
}

const getUpdatedIdAfterConnections = (element) => {
	const prevSlide = slides.value[slideIndex.value - 1]
	const nextSlide = slides.value[slideIndex.value + 1]

	let id = getElementId(prevSlide, element)

	if (!id && currentSlide.value?.transition === 'Magic Move') {
		id = getElementId(nextSlide, element)
	}

	if (!id) {
		id = generateUniqueId()
	}

	return id
}

const createConnectionsForMagicMove = (index) => {
	// adding magic move to last slide changes nothing
	if (index == slides.value.length - 1) return

	const current = slides.value[index]
	const next = slides.value[index + 1]

	current.elements.forEach((currElement) => {
		const refElement = getReferenceElement(currElement, next)
		if (refElement) currElement.id = refElement.id
	})
}

const updateIdsForNextSlides = (fromSlideIndex, element, newId) => {
	while (slides.value[fromSlideIndex]?.transition === 'Magic Move') {
		const nextSlide = slides.value[fromSlideIndex + 1]
		if (!nextSlide) break

		const refElement = getReferenceElement(element, nextSlide)
		if (refElement) refElement.id = newId

		fromSlideIndex++
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
	updateIdsForNextSlides(slideIndex.value, element, id)
}

export { createConnectionsForMagicMove, updateElementId }
