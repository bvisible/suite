import { ref, computed, reactive } from 'vue'
import { call } from 'frappe-ui'

import { presentationId, inSlideShow } from './presentation'
import { activeElementIds } from './element'

import { isEqual } from 'lodash'
import html2canvas from 'html2canvas'

const slideRef = ref(null)

const setSlideRef = (ref) => (slideRef.value = ref)

const slides = ref([])

const slideIndex = ref()

const currentSlide = computed(() => slides.value[slideIndex.value])

const selectionBounds = reactive({
	left: 0,
	top: 0,
	width: 0,
	height: 0,
})

const replaceVideoWithPoster = async (videoElement) => {
	if (!videoElement.poster) return null

	const img = document.createElement('img')
	img.src = videoElement.poster
	img.style.width = videoElement.style.width
	img.style.height = videoElement.style.height
	img.style.objectFit = 'cover'
	img.style.objectPosition = 'center'
	img.style.position = 'absolute'
	img.style.left = videoElement.style.left
	img.style.top = videoElement.style.top

	await videoElement.replaceWith(img)
}

const getFirstElementWithStyle = (container, property) => {
	const walker = document.createTreeWalker(container, NodeFilter.SHOW_ELEMENT, {
		acceptNode: (node) => {
			return node.style[property] ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP
		},
	})

	return walker.nextNode()
}

const getVerticalOffset = (element) => {
	// in order to get correct baseline offset, find first element with font size and line height
	const fontSizeNode = getFirstElementWithStyle(element, 'font-size')
	const lineHeightNode = getFirstElementWithStyle(element, 'line-height')

	const fontSize = parseFloat(fontSizeNode.style.fontSize)
	let lineHeight = lineHeightNode.style.lineHeight

	lineHeight = lineHeight == 'normal' ? fontSize * 1.2 : parseFloat(lineHeight)

	return (lineHeight - fontSize) / 2
}

const getThumbnailHtml = async () => {
	const clone = slideRef.value.cloneNode(true)

	clone.style.position = 'absolute'
	clone.style.left = '-9999px'
	clone.style.top = '0'
	clone.style.transform = 'scale(1)'

	await clone.querySelectorAll('*').forEach(async (element) => {
		if (element.hasAttribute('data-index')) {
			element.style.position = 'absolute'
			// compensate for baseline alignment done by html2canvas for text
			if (element.firstChild.firstChild.hasAttribute('contenteditable')) {
				const verticalOffset = getVerticalOffset(element)
				element.style.top = `${parseFloat(element.style.top) + verticalOffset}px`
			}
		}

		if (element.tagName == 'VIDEO') {
			await replaceVideoWithPoster(element)
		}

		const isEmpty =
			element.tagName == 'DIV' &&
			element.textContent.trim() == '' &&
			element.children.length == 0

		const removeDiv = isEmpty || element.classList.contains('overlay')

		if (removeDiv) {
			element.remove()
		}
	})

	return clone
}

const getSlideThumbnail = async (thumbnailHtml) => {
	document.body.appendChild(thumbnailHtml)

	const canvas = await html2canvas(thumbnailHtml, {
		scale: window.devicePixelRatio,
	})

	document.body.removeChild(thumbnailHtml)

	return canvas.toDataURL('image/png')
}

const slideBounds = reactive({})

const updateSelectionBounds = (newBounds) => {
	Object.assign(selectionBounds, newBounds)
}

const guideVisibilityMap = reactive({
	centerX: false,
	centerY: false,
	leftEdge: false,
	rightEdge: false,
	topEdge: false,
	bottomEdge: false,
})

export {
	slideIndex,
	slides,
	currentSlide,
	slideBounds,
	selectionBounds,
	guideVisibilityMap,
	updateSelectionBounds,
	setSlideRef,
	getSlideThumbnail,
	getThumbnailHtml,
}
