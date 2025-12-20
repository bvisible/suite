import { ref, computed, nextTick, watch } from 'vue'
import { call, createResource } from 'frappe-ui'

import {
	selectionBounds,
	slides,
	slideBounds,
	updateSelectionBounds,
	currentSlide,
	slideIndex,
	updateThumbnail,
	insertSlide,
} from './slide'
import { useTextEditor } from '@/composables/useTextEditor'

import { generateUniqueId, cloneObj } from '../utils/helpers'
import { guessTextColorFromBackground } from '../utils/color'
import { handleUploadedMedia } from '../utils/mediaUploads'
import { presentationId } from './presentation'
import { initElementRefId, updateElementRefId } from './transition'

import { generateHTML } from '@tiptap/core'
import { extensions, patchEmptyParagraphs } from '@/stores/tiptapSetup'

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

			activeElement.value.left = elementLeft + elementWidth / 2
			activeElement.value.top = elementTop + elementHeight / 2
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
		zIndex: currentSlide.value.elements.length + 1,
		transformOrigin: 'center center',
		transform: 'translate(-50%, -50%)',
		left: 0,
		top: 0,
		type: 'text',
		content: getElementContent(elementPresets),
		editorMetadata: {
			lineHeight: 1.5,
		},
	}

	currentSlide.value.elements.push(element)

	updateElementRefId(element)

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
	const posterDataUrl = canvas.toDataURL('image/webp')

	// save the poster as an attachment and return the url for the poster
	return await savePoster.submit(posterDataUrl)
}

const getVideoElementClone = (videoUrl) => {
	const videoElement = document.createElement('video')

	videoElement.crossOrigin = 'anonymous'
	videoElement.preload = 'auto'
	videoElement.muted = true
	videoElement.src = videoUrl
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

const getNaturalSize = async (dataURL) => {
	return new Promise((resolve, reject) => {
		const img = new Image()
		img.onload = () =>
			resolve({
				width: (img.naturalWidth / 2) * slideBounds.scale,
			})
		img.onerror = reject
		img.src = dataURL
	})
}

const addMediaElement = async (file, type) => {
	const src = file.file_url
	const { width } = await getNaturalSize(src)
	let element = {
		id: generateUniqueId(),
		zIndex: currentSlide.value.elements.length + 1,
		width: Math.max(Math.min(width, 800), 30),
		left: 0,
		top: 0,
		opacity: 100,
		type: type,
		src: src,
		attachmentName: file.name,
		borderStyle: 'none',
		borderWidth: 0,
		borderRadius: 0,
		borderColor: '',
		shadowOffsetX: 0,
		shadowOffsetY: 0,
		shadowSpread: 0,
		shadowColor: '#000000ff',
	}
	if (type == 'video') {
		const posterURL = await getVideoPoster(file.file_url)
		element.poster = posterURL
		element.autoplay = false
		element.loop = false
		element.playbackRate = 1
	} else {
		element.invertX = 1
		element.invertY = 1
	}
	currentSlide.value.elements.push(element)

	updateElementRefId(element)

	selectAndCenterElement(element.id)
}

const replaceMediaElement = async (element, fileDoc) => {
	element.src = fileDoc.file_url
	element.attachmentName = fileDoc.name
	if (element.type == 'video') {
		element.poster = await getVideoPoster(fileDoc.file_url)
	}
	updateElementRefId(element)
}

const duplicateElements = async (e, elements, srcSlide) => {
	e?.preventDefault()

	if (srcSlide == null) srcSlide = slideIndex.value

	const displaceByPx = srcSlide == slideIndex.value ? 40 : 0

	let newSelection = []

	elements.forEach((element) => {
		let newElement = JSON.parse(JSON.stringify(element))
		newElement.id = generateUniqueId()
		initElementRefId(newElement, element, srcSlide)
		newElement.zIndex = currentSlide.value.elements.length + 1
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
	await resetFocus()
	const elements = currentSlide.value.elements.filter(
		(element) => !idsToDelete.includes(element.id),
	)
	currentSlide.value.elements = normalizeZIndices(elements)
}

const selectAllElements = (e) => {
	e.preventDefault()
	activeElementIds.value = currentSlide.value.elements.map((element) => element.id)
}

const resetFocus = async () => {
	const index = slideIndex.value

	if (!activeElementIds.value.length) return

	activeElementIds.value = []
	focusElementId.value = null
	pairElementId.value = null

	await nextTick()

	await updateThumbnail(index)
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

const isWithinOverlappingBounds = (outer, inner) => {
	const { left: outerLeft, top: outerTop, right: outerRight, bottom: outerBottom } = outer
	const { left: innerLeft, top: innerTop, right: innerRight, bottom: innerBottom } = inner

	const withinWidth =
		(outerRight >= innerLeft && outerLeft <= innerLeft) ||
		(innerRight >= outerLeft && innerLeft <= outerLeft)

	const withinHeight =
		(outerBottom >= innerTop && outerTop <= innerTop) ||
		(innerBottom >= outerTop && innerTop <= outerTop)

	return withinWidth && withinHeight
}

const getCopiedJSON = () => JSON.stringify(activeElements.value)

const copiedFrom = ref({})

const handleCopy = (e) => {
	if (!activeElements.value.length) return

	e.preventDefault()
	const clipboardJSON = getCopiedJSON()
	e.clipboardData.setData('application/json', clipboardJSON)
	copiedFrom.value = {
		srcPresentation: presentationId.value,
		srcSlide: slideIndex.value,
	}
}

const handlePastedText = async (clipboardText) => {
	await resetFocus()
	addTextElement(clipboardText)
}

const handlePastedJSON = async (json) => {
	const pastedArray = Array.isArray(json) ? json : []

	if (
		pastedArray[0]?.type == 'text' &&
		focusElementId.value &&
		focusElementId.value != pastedArray[0].id
	) {
		activeEditor.value.commands.insertContent(pastedArray[0].content)
		return
	}

	const { srcPresentation, srcSlide } = copiedFrom.value

	if (srcPresentation !== presentationId.value) {
		// if pasted elements are from a different presentation
		// add file attachments correctly to current presentation + update docnames in json
		json = await call('slides.slides.doctype.presentation.presentation.get_updated_json', {
			presentation: presentationId.value,
			json: json,
		})
	}

	duplicateElements(null, json, srcSlide)
}

const handleSvgText = (svgText) => {
	const svgBlob = new Blob([svgText], { type: 'image/svg+xml' })
	const svgFile = new File([svgBlob], 'pasted-image.svg', { type: 'image/svg+xml' })
	handleUploadedMedia([{ kind: 'file', getAsFile: () => svgFile }])
}

const addFixedWidthToElement = (deltaWidth) => {
	const elementDiv = document.querySelector(`[data-index="${activeElement.value.id}"]`)
	if (elementDiv) {
		const rect = elementDiv.getBoundingClientRect()
		activeElement.value.width = rect.width
	}
}

const { initTextEditor, activeEditor } = useTextEditor()
let editorOldText = ''

const getEditorHTML = () => {
	const html = activeEditor.value.getHTML()
	return patchEmptyParagraphs(html)
}

const updateElementContent = (element) => {
	const { wasUpdated, updatedHTML } = getEditorHTML()
	const currentText = activeEditor.value.getText()

	if (editorOldText == currentText && !wasUpdated) return

	updateElementRefId(element)

	element.content = updatedHTML
	editorOldText = currentText
}

const blurAndSaveContent = (element) => {
	activeEditor.value.setEditable(false)
	activeEditor.value.commands.blur()

	if (activeEditor.value.isEmpty) {
		deleteElements(null, [element.id])
	} else {
		updateElementContent(element)
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
			blurAndSaveContent(oldElement)
		}

		nextTick(() => {
			activeEditor.value?.destroy()
			initEditorForElement(element)
			editorOldText = activeEditor.value?.getText()
		})
	},
)

const normalizeZIndices = (elements) => {
	const els = cloneObj(elements).sort((a, b) => {
		const zIndexA = a.zIndex || 1
		const zIndexB = b.zIndex || 1

		return zIndexA - zIndexB
	})

	els.forEach((el, index) => {
		el.zIndex = index + 1
	})

	elements.forEach((el) => {
		const updatedElement = els.find((e) => e.id == el.id)
		el.zIndex = updatedElement.zIndex
	})

	return elements
}

const updatePosition = (axis, value) => {
	const property = axis == 'X' ? 'left' : 'top'

	const delta = value - selectionBounds[property]

	activeElements.value.forEach((element) => {
		element[property] += delta
	})

	selectionBounds[property] = value
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
	handleSvgText,
	handlePastedText,
	handlePastedJSON,
	addFixedWidthToElement,
	deleteAttachments,
	setEditableState,
	replaceMediaElement,
	normalizeZIndices,
	isWithinOverlappingBounds,
	updatePosition,
}
