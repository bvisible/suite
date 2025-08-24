<template>
	<div
		class="flex h-screen w-screen select-none flex-col overflow-hidden"
		@click="focusedSlide = null"
	>
		<Navbar :primaryButton="primaryButtonProps">
			<template #default>
				<PresentationHeader :title="presentationDoc?.title" />
			</template>
		</Navbar>
		<div class="relative flex h-screen bg-gray-300">
			<SlideContainer
				ref="slideContainer"
				:highlight="slideHighlight"
				v-model:hasOngoingInteraction="hasOngoingInteraction"
			/>

			<NavigationPanel
				class="absolute bottom-0 top-0"
				:showNavigator="showNavigator"
				:recentlyRestored="recentlyRestored"
				@changeSlide="changeSlide"
				@openLayoutDialog="openLayoutDialog('insert', slides.length - 1)"
			/>

			<Toolbar
				@setHighlight="setHighlight"
				@openLayoutDialog="openLayoutDialog('insert')"
				@duplicate="duplicateSlide"
				@delete="deleteSlide"
			/>

			<PropertiesPanel
				class="absolute bottom-0 right-0 top-0"
				@openLayoutDialog="openLayoutDialog('replace')"
			/>
		</div>

		<LayoutDialog
			v-if="presentationDoc"
			v-model="showLayoutDialog"
			:theme="presentationDoc.theme"
			:layouts="layoutResource.data"
			@insert="(layoutId) => handleInsertSlide(layoutId)"
		/>
	</div>
</template>

<script setup>
import { ref, watch, computed, useTemplateRef, nextTick, onDeactivated, onActivated, h } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useDebouncedRefHistory, watchIgnorable } from '@vueuse/core'

import { toast } from 'frappe-ui'

import { Presentation } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import Toolbar from '@/components/Toolbar.vue'
import LayoutDialog from '@/components/LayoutDialog.vue'

import {
	presentationId,
	hasStateChanged,
	savePresentationDoc,
	layoutResource,
	initPresentationDoc,
	presentationDoc,
	historyControl,
	historyState,
	initHistory,
	ignoreUpdates,
} from '@/stores/presentation'
import {
	slides,
	slideIndex,
	currentSlide,
	selectionBounds,
	updateSelectionBounds,
	updateThumbnail,
	lastThumbnailTime,
	focusedSlide,
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

import { generateUniqueId } from '@/utils/helpers'

import { activeEditor } from '@/composables/useTextEditor'

let autosaveInterval = null
let thumbnailInterval = null

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => startSlideShow(),
}

const props = defineProps({
	presentationId: String,
	slug: String,
	activeSlideId: {
		type: Number,
		required: true,
	},
})

const router = useRouter()

const slideContainerRef = useTemplateRef('slideContainer')
const dropTargetRef = useTemplateRef('dropTarget')

const showNavigator = ref(true)
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

const saveSlide = (e) => {
	e.preventDefault()
	resetAndSave()
}

const toggleSlideNavigator = () => {
	if (!activeElementIds.value.length || activeElement.value.type != 'text') {
		showNavigator.value = !showNavigator.value
	}
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
			if (e.metaKey) duplicateElements(e, activeElements.value, 40)
			break
	}
}

const handleSlideShortcuts = (e) => {
	switch (e.key) {
		case 'ArrowUp':
			changeSlide(slideIndex.value - 1)
			break
		case 'ArrowDown':
			changeSlide(slideIndex.value + 1)
			break
		case 'Delete':
		case 'Backspace':
			deleteSlide()
			break
		case 'd':
			if (e.metaKey) duplicateSlide(e)
			break
	}
}

const handleGlobalShortcuts = (e) => {
	switch (e.key) {
		case 'Escape':
			resetFocus()
			break
		case 't':
			addTextElement()
			break
		case 'b':
			if (e.metaKey) toggleSlideNavigator()
			break
		case 'a':
			if (e.metaKey) selectAllElements(e)
			break
		case 's':
			if (e.metaKey) saveSlide(e)
			break
		case 'n':
			if (e.ctrlKey) {
				e.preventDefault()
				openLayoutDialog('insert')
			}
			break
		case 'F5':
			e.preventDefault()
			startSlideShow()
			break
	}
}

const recentlyRestored = ref(false)

const handleHistoryOperation = async (operation) => {
	if (operation == 'undo') await historyControl.undo()
	else if (operation == 'redo') await historyControl.redo()

	const slideToFocus = historyState.value.activeSlide
	const elementsToFocus = [...historyState.value.elementIds]

	ignoreUpdates(() => {
		slides.value = JSON.parse(JSON.stringify(historyState.value.slides))
	})

	const onActiveSlide = slideIndex.value == slideToFocus

	if (!onActiveSlide) {
		await changeSlide(slideToFocus)

		recentlyRestored.value = true
		setTimeout(() => {
			recentlyRestored.value = false
		}, 1000)
	}

	if (activeElementIds.value != elementsToFocus) {
		activeElementIds.value = elementsToFocus
	}
	nextTick(() => {
		updateThumbnail(slideToFocus)
	})
}

const handleUndoRedo = (e) => {
	if (activeEditor.value?.isEditable) {
		e.stopPropagation()
		return
	}

	if (historyControl.canRedo.value && e.shiftKey && e.metaKey) {
		e.preventDefault()
		handleHistoryOperation('redo')
	} else if (historyControl.undoStack.value.length > 1 && e.metaKey) {
		e.preventDefault()
		handleHistoryOperation('undo')
	}
}

const handleKeyDown = (e) => {
	if (e.key == 'z') return handleUndoRedo(e)
	const editingText =
		document.activeElement.getAttribute('contenteditable') ||
		document.activeElement.tagName == 'INPUT' ||
		focusElementId.value != null

	if (editingText) return
	handleGlobalShortcuts(e)

	activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

const startSlideShow = async () => {
	await resetFocus()
	saveChanges()

	router.replace({
		name: 'Slideshow',
		params: { presentationId: props.presentationId },
		query: { slide: props.activeSlideId },
	})
}

const handleAutoSave = () => {
	if (hasOngoingInteraction.value || focusElementId.value != null) return
	saveChanges()
}

const dirtySince = ref(null)

const handleThumbnailGeneration = async (index) => {
	if (!slides.value || hasOngoingInteraction.value || focusElementId.value != null) return

	if (dirtySince.value != null && dirtySince.value > lastThumbnailTime.value) {
		await updateThumbnail(index)
	}
}

const changeSlide = async (index) => {
	if (index < 0 || index >= slides.value.length) return

	const oldIndex = slideIndex.value

	await resetFocus()

	focusedSlide.value = null

	await router.replace({
		query: { slide: index + 1 },
	})
}

const getNewSlide = (toDuplicate = false, layoutId) => {
	let layout = null

	if (toDuplicate) {
		layout = currentSlide.value
	} else {
		layout = layoutResource.data.find((l) => l.name == layoutId)
	}

	const slide = {}
	if (layout) {
		slide.background = layout.background
		slide.transition = layout.transition
		slide.transitionDuration = layout.transitionDuration
		slide.thumbnail = layout.thumbnail
		slide.elements = layout.elements.map((element) => {
			return {
				...element,
				id: generateUniqueId(),
			}
		})
	}

	// override metadata and generate unique IDs for elements
	slide.name = ''
	slide.parent = presentationId.value

	return slide
}

const insertSlide = (index, layoutId, toDuplicate) => {
	if (toDuplicate || !index) index = slideIndex.value

	const newSlide = getNewSlide(toDuplicate, layoutId)

	slides.value.splice(index + 1, 0, newSlide)
	slides.value.forEach((slide, index) => {
		slide.idx = index + 1
	})

	changeSlide(index + 1)
}

const deleteSlide = () => {
	if (focusedSlide.value == null) return

	const deleteIndex = focusedSlide.value

	// if there is only one slide, reset the slide state instead of deleting
	const totalLength = slides.value.length

	if (totalLength == 1) {
		slides.value[0].elements = []
		focusedSlide.value = null
		return
	}

	// delete the current slide
	slides.value = slides.value.filter((slide, i) => {
		return i != deleteIndex
	})
	slides.value.forEach((slide, index) => {
		slide.idx = index + 1
	})

	if (deleteIndex == totalLength - 1) {
		// if last slide is deleted, switch to previous slide since no slide at current index
		changeSlide(deleteIndex - 1)
		focusedSlide.value = deleteIndex - 1
	}
}

const duplicateSlide = (e) => {
	e.preventDefault()

	insertSlide(slideIndex.value, null, true)
}

const replaceSlide = (layoutId) => {
	const index = slideIndex.value
	const newSlide = getNewSlide(false, layoutId)

	slides.value.splice(index, 1, newSlide)
	slides.value.forEach((slide, index) => {
		slide.idx = index + 1
	})
}

const resetAndSave = async () => {
	await resetFocus()
	if (!isDirty.value) {
		toast.info('No changes to save')
		return
	}
	const toastProps = {
		loading: `Saving ...`,
		success: () => `Saved`,
		error: () => 'Could not save presentation. Please try again.',
	}
	toast.promise(saveChanges(), toastProps)
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
	}, 1000)
}

const loadPresentation = async (id) => {
	initHistory()
	presentationDoc.value = await initPresentationDoc(id)
	updateRoute(presentationDoc.value.slug)
	layoutResource.fetch({ theme: presentationDoc.value.theme })
	initIntervals()
}

onActivated(() => {
	const id = props.presentationId
	if (!id) return
	loadPresentation(id)

	document.addEventListener('keydown', handleKeyDown)
})

onDeactivated(async () => {
	clearInterval(autosaveInterval)
	clearInterval(thumbnailInterval)
	await resetFocus()
	savePresentation()

	document.removeEventListener('keydown', handleKeyDown)
})

const showLayoutDialog = ref(false)
const layoutAction = ref('')
const insertIndex = ref(null)

const openLayoutDialog = (action, index) => {
	showLayoutDialog.value = true
	layoutAction.value = action
	insertIndex.value = index
}

const handleInsertSlide = (layoutId) => {
	if (layoutAction.value == 'replace') {
		replaceSlide(layoutId)
	} else {
		insertSlide(insertIndex.value, layoutId)
	}
	insertIndex.value = null
}

const isDirty = computed(() => {
	if (!presentationDoc.value || !slides.value) return false

	const original = JSON.parse(JSON.stringify(presentationDoc.value.slides || []))
	const current = JSON.parse(JSON.stringify(slides.value || []))

	return hasStateChanged(original, current)
})

const isSaving = ref(false)

const savePresentation = async () => {
	isSaving.value = true
	try {
		await savePresentationDoc()
	} catch (error) {
		console.error('Error saving presentation:', error)
	} finally {
		isSaving.value = false
	}
}

const saveChanges = async () => {
	if (!isDirty.value || isSaving.value) return

	await savePresentation()
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
		slideIndex.value = parseInt(index) - 1 || 0
	},
	{ immediate: true },
)
</script>
