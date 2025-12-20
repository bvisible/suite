import { slides, slideIndex, currentSlide } from '@/stores/slide'
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

const getReferenceElementOnSlide = (slide, currElement) => {
	if (!slide) return null

	for (const element of slide.elements) {
		if (element.type != currElement.type) continue

		if (canCreateConnection(currElement, element)) {
			return element
		}
	}
}

const getReferenceElement = (element) => {
	const prevSlide = slides.value[slideIndex.value - 1]
	const nextSlide = slides.value[slideIndex.value + 1]

	let el = getReferenceElementOnSlide(prevSlide, element)
	let onPrev = true

	if (!el && currentSlide.value?.transition === 'Magic Move') {
		el = getReferenceElementOnSlide(nextSlide, element)
		onPrev = false
	}

	return { el, onPrev }
}

const createConnectionsForMagicMove = (index) => {
	// adding magic move to last slide changes nothing
	if (index == slides.value.length - 1) return

	const currentSlide = slides.value[index]
	const nextSlide = slides.value[index + 1]

	currentSlide.elements.forEach((currElement) => {
		const refElement = getReferenceElementOnSlide(nextSlide, currElement)
		if (refElement) {
			const refId = generateUniqueId()
			currElement.refId = refId
			refElement.refId = refId
			// update refs till magic move series ends on both sides
			updateRefIdsAcrossSlides(index, currElement, refId, false)
			updateRefIdsAcrossSlides(index, currElement, refId, true)
		}
	})
}

const isAffectedByMagicMove = (slideIndex) => {
	const prevSlide = slides.value[slideIndex - 1]
	const currentSlide = slides.value[slideIndex]

	return prevSlide?.transition === 'Magic Move' || currentSlide?.transition === 'Magic Move'
}

const updateElementRefId = (element) => {
	const needsUpdate = isAffectedByMagicMove(slideIndex.value)
	if (!needsUpdate) return

	const { el, onPrev } = getReferenceElement(element)
	if (el) {
		const refId = generateUniqueId()
		element.refId = refId
		el.refId = refId
		// update refs till magic move series ends on both sides
		updateRefIdsAcrossSlides(slideIndex.value, element, refId, onPrev)
		updateRefIdsAcrossSlides(slideIndex.value, element, refId, !onPrev)
	} else {
		element.refId = null
	}
}

const isSrcElementConnected = (srcElement) => {
	const refIdToCheck = srcElement?.refId
	if (!refIdToCheck) return false

	return currentSlide.value.elements.some((el) => el.refId == refIdToCheck)
}

const isSrcSlideInMagicMove = (srcSlide) => {
	const prevSlideIndex = slideIndex.value - 1

	return srcSlide === prevSlideIndex
		? slides.value[prevSlideIndex]?.transition === 'Magic Move'
		: currentSlide.value?.transition === 'Magic Move'
}

const initElementRefId = (newElement, src, srcSlide) => {
	newElement.refId = null

	if (srcSlide !== slideIndex.value - 1 && srcSlide !== slideIndex.value + 1) return

	const srcElement = slides.value[srcSlide].elements.find((el) => el.id == src.id)

	if (isSrcElementConnected(srcElement) || !isSrcSlideInMagicMove(srcSlide)) return

	const refId = generateUniqueId()
	newElement.refId = refId
	srcElement.refId = refId

	const isForward = srcSlide < slideIndex.value
	updateRefIdsAcrossSlides(slideIndex.value, newElement, refId, isForward)
}

const updateRefIdsAcrossSlides = (fromSlideIndex, element, refId, isForward) => {
	let i = isForward ? fromSlideIndex + 1 : fromSlideIndex - 1

	while (i >= 0 && i < slides.value.length) {
		const slide = slides.value[i]
		const transition = isForward ? slides.value[i - 1]?.transition : slide.transition
		const hasTransition = transition === 'Magic Move'

		if (!hasTransition) break

		const refElement = getReferenceElementOnSlide(slide, element)
		if (refElement) {
			refElement.refId = refId
		}

		i += isForward ? 1 : -1
	}
}

export { createConnectionsForMagicMove, initElementRefId, updateElementRefId }
