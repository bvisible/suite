import { ref, computed, nextTick, watch } from 'vue'
import { call, createResource } from 'frappe-ui'

import { selectionBounds, slides, slideBounds, updateSelectionBounds, currentSlide } from './slide'
import { useTextEditor } from '@/composables/useTextEditor'

import { generateUniqueId } from '../utils/helpers'
import { guessTextColorFromBackground } from '../utils/color'
import { handleUploadedMedia } from '../utils/mediaUploads'
import { presentationId } from './presentation'

import { generateHTML } from '@tiptap/core'
import { extensions } from '@/stores/tiptapSetup'

const activeElementIds = ref([])
const focusElementId = ref(null)
const pairElementId = ref(null)

const activeElements = computed(() => {
	let elements = []
	currentSlide.value.elements.forEach((element) => {
		if (activeElementIds.value.includes(element.id)) {
			elements.push(element)
		}
	})
	return elements
})

const activeElement = computed(() => {
	if (focusElementId.value) {
		return currentSlide.value.elements.find((element) => element.id === focusElementId.value)
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

			const elementLeft = (slideWidth - elementWidth) / 2
			const elementTop = (slideHeight - elementHeight) / 2

			updateSelectionBounds({
				left: elementLeft,
				top: elementTop,
			})

			activeElement.value.left = elementLeft
			activeElement.value.top = elementTop
		})
	})
}

const getElementContent = (element) => {
	const contentJSON = {
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
									letterSpacing: element.letterSpacing,
									opacity: 100,
								},
							},
						],
					},
				],
			},
		],
	}

	return generateHTML(contentJSON, extensions)
}

const addTextElement = async (text) => {
	const elementPresets = {
		textAlign: 'left',
		fontSize: 28,
		fontFamily: 'Inter',
		color: guessTextColorFromBackground(currentSlide.value.background),
		innerText: text,
		letterSpacing: 0,
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

	currentSlide.value.elements.push(element)

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
		borderColor: '',
		shadowOffsetX: 0,
		shadowOffsetY: 0,
		shadowSpread: 1,
		shadowColor: '#000000ff',
	}
	if (type == 'video') {
		element.poster = await getVideoPoster(file.file_url)
		element.autoplay = false
		element.loop = false
		element.playbackRate = 1
	} else {
		element.invertX = 1
		element.invertY = 1
	}
	currentSlide.value.elements.push(element)
	selectAndCenterElement(element.id)
}

const duplicateElements = async (e, elements, displaceByPx = 0) => {
	e?.preventDefault()

	let newSelection = []

	elements.forEach((element) => {
		let newElement = JSON.parse(JSON.stringify(element))
		newElement.id = generateUniqueId()
		newElement.top += displaceByPx
		newElement.left += displaceByPx
		currentSlide.value.elements.push(newElement)
		newSelection.push(newElement.id)
	})

	nextTick(() => (activeElementIds.value = newSelection))
}

const isFileDocUsed = (element) => {
	return slides.value.some((slide) => {
		if (!slide.elements) return false

		return slide.elements.some((el) => el.id !== element.id && el.src === element.src)
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
	const idsToDelete = ids || activeElementIds.value
	resetFocus()
	nextTick(() => {
		currentSlide.value.elements = currentSlide.value.elements.filter((element) => {
			return !idsToDelete.includes(element.id)
		})
	})
}

const selectAllElements = (e) => {
	e.preventDefault()
	activeElementIds.value = currentSlide.value.elements.map((element) => element.id)
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

const { initTextEditor, activeEditor } = useTextEditor()
let editorOldText = ''

const updateElementContent = (id) => {
	const currentText = activeEditor.value.getText()
	if (editorOldText == currentText) return

	const element = currentSlide.value.elements.find((el) => el.id == id)
	element.content = activeEditor.value.getHTML()
	editorOldText = currentText
}

const blurAndSaveContent = (elementId) => {
	activeEditor.value.setEditable(false)
	activeEditor.value.commands.blur()

	if (activeEditor.value.isEmpty) {
		deleteElements(null, [elementId])
	} else {
		updateElementContent(elementId)
	}
}

const setEditableState = () => {
	activeEditor.value.setEditable(true)
	activeEditor.value.commands.focus()
	activeEditor.value.commands.setTextSelection({
		from: 0,
		to: activeEditor.value.state.doc.content.size,
	})
}

const initEditorForElement = (element) => {
	if (element?.type == 'text') {
		const isEditable = focusElementId.value == element.id
		initTextEditor(element.id, element.content, element.editorMetadata, isEditable)

		if (isEditable) setEditableState()
	}
}

watch(
	() => activeElement.value,
	(element, oldElement) => {
		if (oldElement?.type == 'text') {
			blurAndSaveContent(oldElement.id)
		}

		nextTick(() => {
			activeEditor.value?.destroy()
			initEditorForElement(element)
			editorOldText = activeEditor.value?.getText()
		})
	},
)

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
	setEditableState,
}
