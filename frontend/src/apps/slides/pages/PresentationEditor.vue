<template>
	<div
		class="flex h-screen w-screen select-none flex-col overflow-hidden"
		@click="focusedSlide = null"
	>
		<EditorNavbar :readonlyMode="readonlyMode" @startSlideShow="startSlideShow()" />

		<div class="relative flex h-screen bg-gray-300">
			<SlideContainer
				ref="slideContainer"
				v-if="presentationDoc"
				:readonlyMode="readonlyMode"
				:highlight="slideHighlight"
				v-model:hasOngoingInteraction="hasOngoingInteraction"
				@changeSlide="changeEditorSlide"
			/>

			<NavigationPanel
				class="absolute bottom-0 top-0"
				:readonlyMode="readonlyMode"
				:recentlyRestored="recentlyRestored"
				@changeSlide="changeEditorSlide"
				@addEmptySlide="addEmptySlide(null, slidesLength - 1)"
			/>

			<Toolbar
				v-if="!readonlyMode"
				@setHighlight="setHighlight"
				@toggleLayoutView="toggleLayoutView"
				@addEmptySlide="addEmptySlide"
				@duplicate="duplicateSlide"
				@delete="deleteSlide(true)"
			/>

			<PropertiesPanel
				v-if="!readonlyMode"
				class="absolute bottom-0 right-0 top-0"
				:showLayoutsView="showLayoutsView"
			/>
		</div>
	</div>
</template>

<script setup>
import {
	ref,
	watch,
	computed,
	useTemplateRef,
	nextTick,
	onDeactivated,
	onActivated,
	provide,
	onMounted,
	onBeforeUnmount,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { toast } from 'frappe-ui'

import EditorNavbar from '@/components/EditorNavbar.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import Toolbar from '@/components/Toolbar.vue'

import {
	presentationId,
	initPresentationDoc,
	presentationDoc,
	historyControl,
	historyState,
	initHistory,
	ignoreUpdates,
	unsyncedPresentationRecord,
	slidesLength,
	historyMetadata,
	templateList,
	templateListResource,
	presentationTheme,
	readonlyMode,
	showLayoutsView,
} from '@/stores/presentation'
import {
	slides,
	slideIndex,
	selectionBounds,
	updateSelectionBounds,
	updateThumbnail,
	lastThumbnailTime,
	focusedSlide,
	insertSlide,
	getNewSlide,
	setSlideIndex,
	changeEditorSlide,
	deleteSlide,
	insertDuplicateSlide,
	duplicateSlide,
	addEmptySlide,
} from '@/stores/slide'
import {
	resetFocus,
	activeElementIds,
	activeElement,
	focusElementId,
	deleteElements,
	duplicateElements,
	addTextElement,
	selectAllElements,
	activeElements,
} from '@/stores/element'

import { useTextEditor } from '@/composables/useTextEditor'
import { useShortcuts } from '@/composables/useShortcuts'

import { cloneObj, generateUniqueId, isCmdOrCtrl } from '@/utils/helpers'
import {
	saveChanges,
	dirtySince,
	isDirty,
	syncPresentationToServer,
	syncThumbnail,
} from '@/stores/saving'
import { startSlideShow } from '@/stores/slideshow'

const { activeEditor, toggleMark } = useTextEditor()

let autosaveInterval = null
let thumbnailInterval = null

const props = defineProps({
	presentationId: String,
	slug: String,
	activeSlideId: {
		type: Number,
		required: true,
	},
	editorAccess: {
		type: String,
		default: 'none',
	},
})

const router = useRouter()

const slideContainerRef = useTemplateRef('slideContainer')
const dropTargetRef = useTemplateRef('dropTarget')

const slideHighlight = ref(false)
const hasOngoingInteraction = ref(false)

const setHighlight = (value) => {
	slideHighlight.value = value
}

const handleArrowKeys = (key) => {
	let dx = 0
	let dy = 0

	if (key == 'ArrowLeft') dx = -1
	else if (key == 'ArrowRight') dx = 1
	else if (key == 'ArrowUp') dy = -1
	else if (key == 'ArrowDown') dy = 1

	updateSelectionBounds({
		left: selectionBounds.left + dx,
		top: selectionBounds.top + dy,
	})

	activeElements.value.forEach((element) => {
		element.left += dx
		element.top += dy
	})
}

const handleElementShortcuts = (e) => {
	switch (e.key) {
		case 'ArrowLeft':
		case 'ArrowRight':
		case 'ArrowUp':
		case 'ArrowDown':
			handleArrowKeys(e.key)
			break
		case 'Delete':
		case 'Backspace':
			deleteElements(e)
			break
		case 'd':
			if (isCmdOrCtrl(e)) duplicateElements(e, activeElements.value)
			break
		case 'b':
			if (activeEditor.value) toggleMark('bold')
			break
		case 'i':
			if (activeEditor.value) toggleMark('italic')
			break
		case 'u':
			if (activeEditor.value) toggleMark('underline')
			break
	}
}

const handleGlobalShortcuts = (e) => {
	if (isCmdOrCtrl(e) && e.code === 'KeyP') {
		e.preventDefault()
		startSlideShow()
		return
	}

	switch (e.key) {
		case 'Escape':
			resetFocus()
			break
		case 't':
			addTextElement()
			break
		case 'b':
			if (isCmdOrCtrl(e)) toggleSlideNavigator()
			break
		case 'a':
			if (isCmdOrCtrl(e)) selectAllElements(e)
			break
		case 's':
			if (isCmdOrCtrl(e)) saveSlide(e)
			break
		case 'Enter':
			addEmptySlide(e)
			break
		case 'F5':
			e.preventDefault()
			startSlideShow()
			break
	}
}

const recentlyRestored = ref(false)

const getRestoredSlideId = (oldList, newList) => {
	let restoredId = ''
	newList.forEach((slide, index) => {
		if (!oldList.find((s) => s.name === slide.name)) {
			restoredId = index
		}
	})
	return restoredId
}

const getPrevToDeletedSlideId = (oldList, newList) => {
	let prevId = null
	oldList.forEach((slide, index) => {
		if (!newList.find((s) => s.name === slide.name)) {
			prevId = index - 1
		}
	})
	return prevId
}

const wereSlidesReordered = (oldList, newList) => {
	if (oldList.length !== newList.length) return false

	for (let i = 0; i < newList.length; i++) {
		if (oldList[i] && oldList[i].name !== newList[i].name) {
			return true
		}
	}
	return false
}

const getJumpToSlideId = (operation, oldList, newList) => {
	// reordered slides -> the jump to index becomes the slide that was moved
	const didReorder = wereSlidesReordered(oldList, newList)
	if (didReorder && operation == 'undo') return historyMetadata.focusIndexPostUndo
	if (didReorder && operation == 'redo') return historyMetadata.focusIndexPostRedo

	if (oldList.length < newList.length) {
		return getRestoredSlideId(oldList, newList)
	}

	if (oldList.length > newList.length) {
		return getPrevToDeletedSlideId(oldList, newList)
	}

	if (historyControl.undoStack.value.length == 1 && operation == 'undo') {
		return Math.max(0, Math.min(slideIndex.value, slidesLength.value - 1))
	}

	const slideId = historyState.value.activeSlide
	return slides.value.findIndex((slide) => slide.name === slideId)
}

const restoreState = (state, jumpToSlideId) => {
	ignoreUpdates(() => {
		slides.value = JSON.parse(JSON.stringify(state)).map((slide, idx) => {
			if (idx === jumpToSlideId) {
				slide.thumbnail = ''
			}
			return slide
		})
		slidesLength.value = slides.value.length
	})
}

const jumpToSlide = async (operation, oldList, newList) => {
	const jumpToSlideId = getJumpToSlideId(operation, oldList, newList)
	const onActiveSlide = jumpToSlideId == slideIndex.value

	if (!onActiveSlide && jumpToSlideId != null) {
		await changeEditorSlide(jumpToSlideId, false)

		recentlyRestored.value = true
		setTimeout(() => {
			recentlyRestored.value = false
		}, 1000)
	}

	return jumpToSlideId
}

const jumpToActiveElements = () => {
	const elementsToFocus = [...historyState.value.elementIds]

	if (activeElementIds.value != elementsToFocus) {
		activeElementIds.value = elementsToFocus
	}
}

const handleHistoryOperation = async (operation) => {
	activeElementIds.value = []

	if (operation == 'undo') await historyControl.undo()
	else if (operation == 'redo') await historyControl.redo()

	const oldList = JSON.parse(JSON.stringify(slides.value))
	const newList = JSON.parse(JSON.stringify(historyState.value.slides))

	const jumpToSlideId = await jumpToSlide(operation, oldList, newList)

	restoreState(historyState.value.slides, jumpToSlideId)

	await nextTick()

	updateThumbnail(jumpToSlideId)

	nextTick(() => {
		jumpToActiveElements()
	})
}

const handleUndoRedo = (e) => {
	e.preventDefault()

	if (activeEditor.value?.isEditable) {
		e.stopPropagation()
		return
	}

	if (isCmdOrCtrl(e) && e.shiftKey && historyControl.canRedo.value) {
		handleHistoryOperation('redo')
	} else if (isCmdOrCtrl(e) && historyControl.undoStack.value.length > 1) {
		handleHistoryOperation('undo')
	}
}

const handleKeyDown = (e) => {
	const editingText =
		document.activeElement.getAttribute('contenteditable') ||
		document.activeElement.tagName == 'INPUT' ||
		focusElementId.value != null

	if (editingText) return

	if (e.key == 'z') return handleUndoRedo(e)

	handleGlobalShortcuts(e)

	activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

const handleAutoSave = () => {
	if (hasOngoingInteraction.value || focusElementId.value != null) return
	saveChanges()
}

const handleThumbnailGeneration = async (index) => {
	if (!slides.value || hasOngoingInteraction.value || focusElementId.value != null) return

	if (dirtySince.value != null && dirtySince.value > lastThumbnailTime.value) {
		await updateThumbnail(index)
	}
}

const updateRoute = async (slug) => {
	if (props.slug == slug) return
	router.replace({
		name: 'PresentationEditor',
		params: { presentationId: presentationId.value, slug: slug },
		query: { slide: slideIndex.value + 1 },
	})
}

const initIntervals = () => {
	autosaveInterval = setInterval(handleAutoSave, 500)
	thumbnailInterval = setInterval(() => {
		handleThumbnailGeneration(slideIndex.value)
	}, 1500)
}

const loadPresentation = async (id) => {
	presentationDoc.value = await initPresentationDoc(id)
	setSlideIndex(props.activeSlideId)
	updateRoute(presentationDoc.value.slug)
	initIntervals()
}

const loadPresentationInReadonlyMode = async (id) => {
	presentationDoc.value = await initPresentationDoc(id, true)
	setSlideIndex(props.activeSlideId)
	updateRoute(presentationDoc.value.slug)
}

const route = useRoute()

const updateUnsyncedRecord = () => {
	unsyncedPresentationRecord.value = {
		...unsyncedPresentationRecord.value,
		modified: presentationDoc.value.modified,
		thumbnail: slides.value[0]?.thumbnail,
	}
}

const layoutAction = ref('')

const toggleLayoutView = () => {
	showLayoutsView.value = !showLayoutsView.value
}

const handleMounted = () => {
	if (!templateList.value.length && !readonlyMode.value) {
		templateListResource.fetch()
	}
	const id = props.presentationId
	if (!id) return
	if (readonlyMode.value) {
		loadPresentationInReadonlyMode(id)
	} else {
		loadPresentation(id)
	}
}

const handleBeforeUnmount = () => {
	updateUnsyncedRecord()
	clearInterval(autosaveInterval)
	clearInterval(thumbnailInterval)

	if (router.currentRoute.value.name !== 'Slideshow') {
		resetFocus()
		syncPresentationToServer()
	}
}

watch(
	() => isDirty.value,
	(val) => {
		if (val) {
			dirtySince.value = Date.now()
		}
	},
)

watch(
	() => props.activeSlideId,
	(index) => {
		if (!slides.value.length) return
		setSlideIndex(index)
	},
	{ immediate: true },
)

watch(
	() => props.presentationId,
	() => handleMounted(),
)

onMounted(() => handleMounted())

onBeforeUnmount(() => handleBeforeUnmount())

provide('readonlyMode', readonlyMode)

useShortcuts({
	readonlyMode,
})

watch(
	() => props.editorAccess,
	(doc) => {
		readonlyMode.value = doc === 'view'
	},
)
</script>
