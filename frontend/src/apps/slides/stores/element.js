import { ref, computed, nextTick } from 'vue'
import { call, createResource } from 'frappe-ui'

import { selectionBounds, slide, slideBounds, updateSelectionBounds } from './slide'

import { generateUniqueId } from '../utils/helpers'
import { guessTextColorFromBackground } from '../utils/color'
import { handleUploadedMedia } from '../utils/mediaUploads'
import { presentation, presentationId } from './presentation'

const activeElementIds = ref([])
const focusElementId = ref(null)
const pairElementId = ref(null)

const activeElements = computed(() => {
	let elements = []
	slide.value.elements.forEach((element) => {
		if (activeElementIds.value.includes(element.id)) {
			elements.push(element)
		}
	})
	return elements
})

const activeElement = computed(() => {
	if (focusElementId.value) {
		return slide.value.elements.find((element) => element.id === focusElementId.value)
	} else if (activeElementIds.value.length == 1) {
		return activeElements.value[0]
	}
})

const setActiveElements = (ids, focus = false) => {
	if (ids.length == 1 && activeElementIds.value.includes(ids[0])) return
	activeElementIds.value = ids
	focusElementId.value = null
}

const selectAndCenterElement = (elementId) => {
	const slideWidth = slideBounds.width / slideBounds.scale
	const slideHeight = slideBounds.height / slideBounds.scale

	nextTick(() => {
		setActiveElements([elementId])
		// to allow centering element only after it's rendered in order to correctly calculate its offset from center
		requestAnimationFrame(async () => {
			await nextTick()
			const elementRect = document
				.querySelector(`[data-index="${elementId}"]`)
				.getBoundingClientRect()

			const elementWidth = elementRect.width / slideBounds.scale
			const elementHeight = elementRect.height / slideBounds.scale

			updateSelectionBounds({
				left: (slideWidth - elementWidth) / 2,
				top: (slideHeight - elementHeight) / 2,
			})
		})
	})
}

const getElementContent = (element) => {
	return {
		type: 'doc',
		content: [
			{
				type: 'paragraph',
				attrs: {
					textAlign: element.textAlign || 'center',
				},
				content: [
					{
						type: 'text',
						text: element.innerText || 'Text',
						marks: [
							{
								type: 'textStyle',
								attrs: {
									fontSize: element.fontSize,
									fontFamily: element.fontFamily,
									color: element.color,
									letterSpacing: 0,
									opacity: 100,
								},
							},
						],
					},
				],
			},
		],
	}
}

const addTextElement = async (text) => {
	const elementPresets = {
		textAlign: 'left',
		fontSize: 28,
		fontFamily: 'Arial',
		color: guessTextColorFromBackground(slide.value.background),
		innerText: text,
	}

	const element = {
		id: generateUniqueId(),
		left: 0,
		top: 0,
		type: 'text',
		content: getElementContent(elementPresets),
		editorMetadata: {
			lineHeight: 1.5,
		},
	}

	slide.value.elements.push(element)
	selectAndCenterElement(element.id)
}

const savePoster = createResource({
	url: 'slides.slides.doctype.presentation.presentation.save_base64_thumbnail',
	makeParams: (posterDataUrl) => ({
		presentation_name: presentationId.value,
		base64_data: posterDataUrl,
		prefix: 'poster',
	}),
})

const generatePoster = async (video) => {
	// create a canvas of the size of the video
	const canvas = document.createElement('canvas')
	canvas.width = video.videoWidth
	canvas.height = video.videoHeight

	const context = canvas.getContext('2d')
	// draw the current frame of the video onto the canvas
	context.drawImage(video, 0, 0, canvas.width, canvas.height)
	const posterDataUrl = canvas.toDataURL('image/jpeg')

	// save the poster as an attachment and return the url for the poster
	return await savePoster.submit(posterDataUrl)
}

const getVideoElementClone = (videoUrl) => {
	const videoElement = document.createElement('video')

	videoElement.src = videoUrl
	videoElement.crossOrigin = 'anonymous'
	videoElement.style.position = 'absolute'
	videoElement.style.left = '-9999px'
	videoElement.style.width = '300px'
	videoElement.style.height = 'auto'

	return videoElement
}

const handleVideoCloneDataLoad = async (videoClone, resolve, reject) => {
	try {
		const poster = await generatePoster(videoClone)
		resolve(poster)
	} catch (err) {
		reject(err)
	} finally {
		// remove the video element from the DOM after poster is generated
		document.body.removeChild(videoClone)
	}
}

const getVideoPoster = async (videoUrl) => {
	return new Promise((resolve, reject) => {
		// create a clone of the video element to generate a poster
		// without making the original video visible so there's no flicker
		const videoClone = getVideoElementClone(videoUrl)
		document.body.appendChild(videoClone)

		// we cannot directly capture the poster without data load event
		videoClone.addEventListener(
			'loadeddata',
			() => handleVideoCloneDataLoad(videoClone, resolve, reject),
			{ once: true },
		)

		videoClone.addEventListener(
			'error',
			() => {
				// if video fails to load, don't leave cloned element in the DOM
				document.body.removeChild(videoClone)
				reject(new Error('Failed to load video for poster generation'))
			},
			{ once: true },
		)
	})
}

const addMediaElement = async (file, type) => {
	let element = {
		id: generateUniqueId(),
		width: 300,
		left: 0,
		top: 0,
		opacity: 100,
		type: type,
		src: file.file_url,
		attachmentName: file.name,
		borderStyle: 'none',
		borderWidth: 0,
		borderRadius: 0,
		borderColor: '#000000',
		shadowOffsetX: 0,
		shadowOffsetY: 0,
		shadowSpread: 0,
		shadowColor: '#000000',
	}
	if (type == 'video') {
		element.poster = await getVideoPoster(file.file_url)
		element.autoplay = false
		element.loop = false
		element.playbackRate = 1
	}
	slide.value.elements.push(element)
	selectAndCenterElement(element.id)
}

const duplicateElements = async (e, elements, displaceByPx = 0) => {
	e?.preventDefault()

	let newSelection = []
	const oldElements = elements
	activeElementIds.value = []

	await nextTick()

	oldElements.forEach((element) => {
		let newElement = JSON.parse(JSON.stringify(element))
		newElement.id = generateUniqueId()
		newElement.top += displaceByPx
		newElement.left += displaceByPx
		slide.value.elements.push(newElement)
		newSelection.push(newElement.id)
	})

	nextTick(() => (activeElementIds.value = newSelection))
}

const isFileDocUsed = (element) => {
	return presentation.data.slides.some((slide) => {
		if (!slide.elements) return false

		const elements = JSON.parse(slide.elements)
		return elements.some((el) => el.id !== element.id && el.src === element.src)
	})
}

const deleteAttachments = async (elements) => {
	elements.forEach((element) => {
		if (['image', 'video'].includes(element.type)) {
			if (isFileDocUsed(element)) return

			call('frappe.client.delete', {
				doctype: 'File',
				name: element.attachmentName,
			})
		}
	})
}

const deleteElements = async (e, ids) => {
	deleteAttachments(activeElements.value)
	const idsToDelete = ids || activeElementIds.value
	resetFocus()
	nextTick(() => {
		slide.value.elements = slide.value.elements.filter((element) => {
			return !idsToDelete.includes(element.id)
		})
	})
}

const selectAllElements = (e) => {
	e.preventDefault()
	activeElementIds.value = slide.value.elements.map((element) => element.id)
}

const resetFocus = () => {
	activeElementIds.value = []
	focusElementId.value = null
	pairElementId.value = null
}

const getElementPosition = (elementId) => {
	const elementRect = document
		.querySelector(`[data-index="${elementId}"]`)
		.getBoundingClientRect()

	const elementLeft = (elementRect.left - slideBounds.left) / slideBounds.scale
	const elementTop = (elementRect.top - slideBounds.top) / slideBounds.scale
	const elementRight = elementLeft + elementRect.width / slideBounds.scale
	const elementBottom = elementTop + elementRect.height / slideBounds.scale

	return {
		left: elementLeft,
		top: elementTop,
		right: elementRight,
		bottom: elementBottom,
	}
}

const getCopiedJSON = () => {
	const elementsCopy = JSON.parse(JSON.stringify(activeElements.value))
	elementsCopy.forEach((element) => {
		const { left, top } = getElementPosition(element.id)
		element.left = left
		element.top = top
	})
	return JSON.stringify(elementsCopy)
}

const copiedFromId = ref(null)

const handleCopy = (e) => {
	e.preventDefault()
	const clipboardJSON = getCopiedJSON()
	e.clipboardData.setData('application/json', clipboardJSON)
	copiedFromId.value = presentationId.value
}

const handlePastedText = (clipboardText) => {
	resetFocus()
	addTextElement(clipboardText)
}

const handlePastedJSON = async (json) => {
	if (copiedFromId.value !== presentationId.value) {
		// if pasted elements are from a different presentation
		// add file attachments correctly to current presentation + update docnames in json
		json = await call('slides.slides.doctype.presentation.presentation.get_updated_json', {
			presentation: presentationId.value,
			json: json,
		})
	}
	duplicateElements(null, json)
}

const handlePaste = (e) => {
	e.preventDefault()

	const clipboardItems = e.clipboardData.items
	if (clipboardItems) handleUploadedMedia(clipboardItems)

	const clipboardText = e.clipboardData.getData('text/plain')
	if (clipboardText && !focusElementId.value) handlePastedText(clipboardText)

	const clipboardJSON = e.clipboardData.getData('application/json')
	if (clipboardJSON) handlePastedJSON(JSON.parse(clipboardJSON))
}

const updateElementWidth = (deltaWidth) => {
	const element = activeElement.value

	if (element.width) {
		element.width += deltaWidth
	} else {
		const elementDiv = document.querySelector(`[data-index="${element.id}"]`)
		const width = elementDiv.getBoundingClientRect().width

		element.width = width + deltaWidth
	}
}

export {
	activeElementIds,
	focusElementId,
	pairElementId,
	activeElements,
	activeElement,
	setActiveElements,
	resetFocus,
	addTextElement,
	addMediaElement,
	duplicateElements,
	deleteElements,
	selectAllElements,
	getElementPosition,
	handleCopy,
	handlePaste,
	updateElementWidth,
	deleteAttachments,
}
