<template>
	<div ref="slideContainer" class="flex size-full" @dragenter="showOverlay">
		<!-- when mounting place slide directly in the center of the visible container -->
		<!-- 1/2 width of viewport + 1/2 width of offset caused due to thinner navigation panel -->
		<div ref="slideRef" :style="slideStyles" :class="slideClasses" @contextmenu.prevent>
			<SelectionBox
				ref="selectionBox"
				v-if="!readonlyMode"
				:isDragging
				@mousedown="(e) => handleMouseDown(e)"
				@setIsSelecting="(val) => (isSelecting = val)"
			/>

			<SnapGuides
				:ongoingInteraction="hasOngoingInteraction"
				:visibilityMap="visibilityMap"
			/>

			<SlideElement
				v-for="element in currentSlide?.elements"
				:key="`editor-${element.id}`"
				mode="editor"
				:element
				:elementOffset
				:data-index="element.id"
				:highlight="highlightElement(element)"
				@mousedown="(e) => handleMouseDown(e, element)"
				@clearTimeouts="clearTimeouts"
			/>
		</div>
		<DropTargetOverlay v-show="mediaDragOver" @hideOverlay="hideOverlay" />
		<OverflowContentOverlay />
	</div>
</template>

<script setup>
import {
	ref,
	computed,
	watch,
	useTemplateRef,
	nextTick,
	onMounted,
	onBeforeUnmount,
	provide,
	reactive,
	onActivated,
	onDeactivated,
} from 'vue'
import { useResizeObserver } from '@vueuse/core'

import SnapGuides from '@/components/SnapGuides.vue'
import SelectionBox from '@/components/SelectionBox.vue'
import SlideElement from '@/components/SlideElement.vue'
import DropTargetOverlay from '@/components/DropTargetOverlay.vue'
import OverflowContentOverlay from '@/components/OverflowContentOverlay.vue'

import {
	currentSlide,
	slideBounds,
	selectionBounds,
	updateSelectionBounds,
	setSlideRef,
	insertSlide,
	slideIndex,
} from '@/stores/slide'
import {
	activeElementIds,
	activeElement,
	handleCopy,
	handleSvgText,
	handlePastedText,
	handlePastedJSON,
	focusElementId,
	pairElementId,
	addFixedWidthToElement,
	setEditableState,
} from '@/stores/element'

import { useDragAndDrop } from '@/composables/useDragAndDrop'
import { useResizer } from '@/composables/useResizer'
import { usePanAndZoom } from '@/composables/usePanAndZoom'
import { useSnapping } from '@/composables/useSnapping'

import { getDocFromHTML, isCmdOrCtrl } from '@/utils/helpers'
import { handleUploadedMedia } from '../utils/mediaUploads'

const props = defineProps({
	highlight: Boolean,
	readonlyMode: {
		type: Boolean,
		default: false,
	},
})

const emit = defineEmits(['update:hasOngoingInteraction', 'changeSlide'])

const slideContainerRef = useTemplateRef('slideContainer')
const slideRef = useTemplateRef('slideRef')
const selectionBoxRef = useTemplateRef('selectionBox')

const { isDragging, positionDelta, startDragging } = useDragAndDrop()

const { isResizing, dimensionDelta, currentResizer, resizeCursor, startResize } = useResizer()

const hasOngoingInteraction = computed(() => isDragging.value || isResizing.value)

const { visibilityMap, resistanceMap, handleSnapping } = useSnapping(
	selectionBoxRef,
	slideRef,
	currentResizer,
	hasOngoingInteraction,
)

const { allowPanAndZoom, transform, transformOrigin } = usePanAndZoom(slideContainerRef, slideRef)

const slideClasses = computed(() => {
	const classes = ['absolute', 'h-[540px]', 'w-[960px]', 'shadow-2xl', 'shadow-gray-400']

	const outlineClasses =
		props.highlight || mediaDragOver.value ? ['outline', 'outline-2', 'outline-blue-400'] : []

	const positionClasses = props.readonlyMode
		? ['left-[calc(50%-384.5px)]', 'top-[calc(50%-270px)]']
		: ['left-[calc(50%-512px)]', 'top-[calc(50%-270px)]']

	return [...classes, outlineClasses, positionClasses]
})

const isSelecting = ref(false)

const getSlideCursor = () => {
	if (isDragging.value) return 'move'
	if (isSelecting.value) return 'crosshair'
	if (resizeCursor.value) return resizeCursor.value

	return 'default'
}

const highlightElement = (element) => {
	const toHighlight =
		activeElementIds.value.length > 1 && activeElementIds.value.includes(element.id)
	return toHighlight || pairElementId.value == element.id
}

const slideStyles = computed(() => ({
	transformOrigin: transformOrigin.value,
	transform: transform.value,
	backgroundColor: currentSlide.value?.background || '#ffffff',
	cursor: getSlideCursor(),
	zIndex: 0,
}))

const mediaDragOver = ref(false)

const showOverlay = (e) => {
	e.preventDefault()
	if (props.readonlyMode) return
	mediaDragOver.value = true
}

const hideOverlay = () => {
	mediaDragOver.value = false
}

let dragTimeout, clickTimeout

const clearTimeouts = () => {
	clearTimeout(dragTimeout)
	clearTimeout(clickTimeout)
}

const triggerSelection = (e, id) => {
	if (id) {
		if (!activeElementIds.value.includes(id)) {
			if (isCmdOrCtrl(e) || e.shiftKey) {
				activeElementIds.value = [...activeElementIds.value, id]
			} else activeElementIds.value = [id]
			focusElementId.value = null
		} else if (activeElement.value?.type == 'text') {
			focusElementId.value = id

			setEditableState()
		}
	}
}

const handleMouseUp = (e, id) => {
	clearTimeouts()

	pairElementId.value = null

	if (!isDragging.value) clickTimeout = setTimeout(() => triggerSelection(e, id), 200)
}

const triggerDrag = (e, id) => {
	const notEditable = id && focusElementId.value !== id
	const isMultiSelect = activeElementIds.value.length > 1
	const isNotInSelection = id && !activeElementIds.value.includes(id)

	// prevent drag if multiple are selected and id isn't in the selection
	if (isMultiSelect && isNotInSelection) return

	if (notEditable || isMultiSelect) {
		startDragging(e)

		if (id && !isMultiSelect && activeElementIds.value[0] !== id) {
			activeElementIds.value = [id]
			focusElementId.value = null
		}
	}
}

const handleMouseDown = (e, element) => {
	if (props.readonlyMode) return
	const id = element?.id

	e.stopPropagation()
	e.preventDefault()

	// wait for click to be registered
	// if the click is not registered, it means the user is dragging
	dragTimeout = setTimeout(() => triggerDrag(e, id), 100)

	// if the click is registered ie. mouseup happens before dragTimeout
	// then consider it a selection instead of dragging
	e.target.addEventListener('mouseup', () => handleMouseUp(e, id), { once: true })
}

const scale = computed(() => {
	const matrix = transform.value?.match(/matrix\((.+)\)/)
	if (!matrix) return 1
	return parseFloat(matrix[1].split(', ')[0])
})

const activeDiv = computed(() => {
	if (activeElementIds.value.length != 1) return null
	return document.querySelector(`[data-index="${activeElementIds.value[0]}"]`)
})

useResizeObserver(activeDiv, (entries) => {
	const entry = entries[0]
	const { width, height } = entry.contentRect
	const target = entry.target.getBoundingClientRect()

	// case:
	// when element dimensions are changed not by resizer
	// but by other updates on properties - font size, line height, letter spacing etc.
	updateSelectionBounds({
		width: width,
		height: height,
		left: (target.left - slideBounds.left) / scale.value,
		top: (target.top - slideBounds.top) / scale.value,
	})
})

const togglePanZoom = () => {
	allowPanAndZoom.value = !allowPanAndZoom.value
}

const applyResistance = (axis, delta) => {
	const scaledThreshold = (0.02 * selectionBounds.width) / slideBounds.scale

	const escapeDelta = Math.max(2, Math.min(5, scaledThreshold))

	let useResistanceKeys = []
	let pullDelta = null

	if (axis == 'X') {
		useResistanceKeys = ['left', 'right', 'centerY']
		pullDelta = delta.left
	} else if (axis == 'Y') {
		useResistanceKeys = ['top', 'bottom', 'centerX']
		pullDelta = delta.top
	} else if (axis == null && currentResizer.value) {
		useResistanceKeys = ['left', 'right', 'top', 'bottom', 'centerX', 'centerY']
		pullDelta = delta.width
	}

	const useResistance = useResistanceKeys.some((key) => resistanceMap[key])

	return useResistance && Math.abs(pullDelta) < escapeDelta
}

const updateTotalDeltaForResize = (totalDelta, delta, width) => {
	totalDelta.width = applyResistance(null, delta) ? 0 : width

	// if resisting width change, don't apply top change either otherwise
	// element sticks to one axis and drags on other which shouldn't happen on resize
	if (totalDelta.width === 0) totalDelta.top = 0
}

const getTotalInteractionDelta = (delta, interaction = 'dragging') => {
	const snapDelta = handleSnapping(interaction)

	const left = snapDelta.x || delta.left
	const top = snapDelta.y || delta.top

	const totalDelta = {
		left: applyResistance('X', delta) ? 0 : left,
		top: applyResistance('Y', delta) ? 0 : top,
	}

	const width = snapDelta.width || delta.width

	if (interaction === 'resizing') {
		updateTotalDeltaForResize(totalDelta, delta, width)
	}

	return totalDelta
}

const elementOffset = reactive({
	left: 0,
	top: 0,
	width: 0,
})

const handlePositionChange = (delta) => {
	if (!delta.left && !delta.top) return

	const totalDelta = getTotalInteractionDelta(delta)

	applyPositionDelta(totalDelta)
}

const applyAspectRatio = (offset) => {
	if (!offset) return 0
	const ratio = selectionBounds.width / selectionBounds.height
	return (offset ?? 0) / ratio
}

const validateMinWidth = (width) => {
	const minWidth = activeElement.value.type === 'text' ? 7 : 29
	return width + selectionBounds.width > minWidth
}

const applyPositionDelta = (delta) => {
	if (!delta.left && !delta.top) return

	const deltaLeft = delta.left / slideBounds.scale
	const deltaTop = delta.top / slideBounds.scale

	updateSelectionBounds({
		left: selectionBounds.left + deltaLeft,
		top: selectionBounds.top + deltaTop,
	})

	elementOffset.left += deltaLeft
	elementOffset.top += deltaTop
}

const applyDimensionDelta = (delta) => {
	if (!delta.width) return

	const deltaWidth = delta.width / slideBounds.scale

	elementOffset.width += deltaWidth
}

const handleDimensionChange = (delta) => {
	if (!delta.width || !validateMinWidth(delta.width)) return

	delta.top = applyAspectRatio(delta.top)

	const totalDelta = getTotalInteractionDelta(delta, 'resizing')

	applyPositionDelta(totalDelta)

	if (!activeElement.value.width) addFixedWidthToElement()

	applyDimensionDelta(totalDelta)
}

const updateSlideBounds = () => {
	const slideRect = slideRef.value.getBoundingClientRect()

	slideBounds.width = slideRect.width
	slideBounds.height = slideRect.height
	slideBounds.left = slideRect.left
	slideBounds.top = slideRect.top
	slideBounds.scale = scale.value
}

const handleSlideTransform = () => {
	// wait for the new transform to render before updating dimensions
	nextTick(() => {
		updateSlideBounds()
	})
}

watch(
	() => activeElementIds.value,
	(newVal, oldVal) => {
		selectionBoxRef.value.handleSelectionChange(newVal, oldVal)
	},
)

watch(
	() => transform.value,
	() => {
		if (!transform.value) return
		handleSlideTransform()
	},
)

watch(
	() => positionDelta.value,
	(delta) => {
		handlePositionChange(delta)
	},
)

watch(
	() => dimensionDelta.value,
	(delta) => {
		handleDimensionChange(delta)
	},
)

const handlePastedSlideJSON = async (json) => {
	const index = slideIndex.value

	insertSlide(JSON.parse(json), index)

	emit('changeSlide', index + 1)
}

const isInputElement = (el) => {
	const activeElement = document.activeElement
	return (
		activeElement?.tagName == 'INPUT' ||
		activeElement?.tagName == 'TEXTAREA' ||
		activeElement?.isContentEditable
	)
}

const handleClipboardText = (clipboardText) => {
	if (clipboardText?.trim().startsWith('<svg') && clipboardText?.trim().endsWith('</svg>')) {
		handleSvgText(clipboardText)
	} else if (clipboardText && !focusElementId.value) {
		handlePastedText(clipboardText)
	}
}

const handleClipboardJSON = (clipboardJSON) => {
	const isSlideJSON = !Array.isArray(clipboardJSON) && clipboardJSON.includes('"elements"')
	if (isSlideJSON) {
		return handlePastedSlideJSON(clipboardJSON)
	}
	return handlePastedJSON(JSON.parse(clipboardJSON))
}

const dataURLToFile = (dataURL, filename) => {
	const [meta, base64] = dataURL.split(',')
	const mime = meta.match(/:(.*?);/)[1]
	const binary = atob(base64)
	const len = binary.length
	const buffer = new Uint8Array(len)

	for (let i = 0; i < len; i++) {
		buffer[i] = binary.charCodeAt(i)
	}

	return new File([buffer], filename, {
		type: mime,
		lastModified: Date.now(),
	})
}

const getImageSrcFromHTML = (clipboardTextHTML) => {
	const doc = getDocFromHTML(clipboardTextHTML)
	const img = doc.querySelector('img')

	if (img) return img.src
	return null
}

const handleClipboardTextHTML = (imgSrc) => {
	const file = dataURLToFile(imgSrc, 'pasted-image.png')
	handleUploadedMedia([{ kind: 'file', getAsFile: () => file }])
}

const handlePaste = (e) => {
	// do not override paste event if current element is input or content editable
	if (isInputElement()) return

	e.preventDefault()

	const clipboardTextHTML = e.clipboardData.getData('text/html')
	const imgSrc = getImageSrcFromHTML(clipboardTextHTML)
	if (clipboardTextHTML && imgSrc) return handleClipboardTextHTML(clipboardTextHTML)

	const clipboardJSON = e.clipboardData.getData('application/json')
	if (clipboardJSON) return handleClipboardJSON(clipboardJSON)

	const clipboardText = e.clipboardData.getData('text/plain')
	if (clipboardText) return handleClipboardText(clipboardText)

	const clipboardItems = e.clipboardData.items
	if (clipboardItems) return handleUploadedMedia(clipboardItems)
}

const initSlideAndListeners = () => {
	if (!slideRef.value) return

	setSlideRef(slideRef.value)

	updateSlideBounds()

	document.addEventListener('copy', handleCopy)
	document.addEventListener('paste', handlePaste)
	window.addEventListener('resize', updateSlideBounds)
}

const clearListeners = () => {
	document.removeEventListener('copy', handleCopy)
	document.removeEventListener('paste', handlePaste)
	window.removeEventListener('resize', updateSlideBounds)
}

onMounted(() => initSlideAndListeners())

onActivated(() => initSlideAndListeners())

onDeactivated(() => clearListeners())

onBeforeUnmount(() => clearListeners())

provide('slideDiv', slideRef)
provide('slideContainerDiv', slideContainerRef)
provide('resizer', {
	currentResizer,
	startResize,
})

defineExpose({
	togglePanZoom,
})

const applyInteractionOffsets = () => {
	pairElementId.value = null
	requestAnimationFrame(() => {
		activeElementIds.value.forEach((id) => {
			const element = currentSlide.value.elements.find((el) => el.id === id)
			if (element) {
				element.left += elementOffset.left
				element.top += elementOffset.top
				element.width += elementOffset.width
			}
		})
		elementOffset.left = 0
		elementOffset.top = 0
		elementOffset.width = 0
	})
}

watch(
	() => hasOngoingInteraction.value,
	(newVal, oldVal) => {
		if (oldVal && !newVal) applyInteractionOffsets()
		emit('update:hasOngoingInteraction', newVal)
	},
)
</script>
