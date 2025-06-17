<template>
	<div class="h-screen w-screen flex flex-col select-none overflow-hidden">
		<Navbar :primaryButton="primaryButtonProps">
			<template #default>
				<PresentationHeader />
			</template>
		</Navbar>
		<div
			class="flex relative h-screen"
			:class="!activeElementIds.length ? 'bg-gray-300' : 'bg-gray-100'"
		>
			<NavigationPanel
				class="absolute top-0 bottom-0 z-50"
				:showNavigator="showNavigator"
				@changeSlide="changeSlide"
				@insertSlide="insertSlide"
			/>

			<SlideContainer ref="slideContainer" :highlight="slideHighlight" />

			<Toolbar
				@setHighlight="setHighlight"
				@insert="insertSlide"
				@duplicate="duplicateSlide"
				@delete="deleteSlide"
			/>

			<PropertiesPanel class="absolute top-0 right-0 bottom-0 z-10" />
		</div>
	</div>
</template>

<script setup>
import { ref, watch, computed, useTemplateRef, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'
import { toast } from 'vue-sonner'

import { call } from 'frappe-ui'

import { Presentation } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import DropTargetOverlay from '@/components/DropTargetOverlay.vue'
import Toolbar from '@/components/Toolbar.vue'

import { presentationId, presentation, loadPresentation } from '@/stores/presentation'
import {
	slide,
	slideIndex,
	saveChanges,
	loadSlide,
	selectionBounds,
	updateSelectionBounds,
	updateSlideThumbnail,
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
	toggleTextProperty,
} from '@/stores/element'

import html2canvas from 'html2canvas'

let autosaveInterval = null

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => startSlideShow(),
}

const route = useRoute()
const router = useRouter()

const slideContainerRef = useTemplateRef('slideContainer')
const dropTargetRef = useTemplateRef('dropTarget')

const showNavigator = ref(true)
const slideHighlight = ref(false)

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
		case 'i':
			if (e.metaKey) toggleTextProperty('fontStyle', 'italic')
			break
		case 'u':
			if (e.metaKey) toggleTextProperty('textDecoration', 'underline')
			break
		case 'b':
			if (e.metaKey) toggleTextProperty('fontWeight', 'bold')
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
			if (e.metaKey) selectAllElements()
			break
		case 's':
			if (e.metaKey) saveSlide(e)
			break
	}
}

const handleKeyDown = (e) => {
	const editingText =
		document.activeElement.getAttribute('contenteditable') ||
		document.activeElement.tagName == 'INPUT' ||
		focusElementId.value != null

	if (editingText) return
	handleGlobalShortcuts(e)

	activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

const startSlideShow = () => {
	resetFocus()
	nextTick(() => {
		saveChanges()
	})

	router.replace({
		name: 'Slideshow',
		params: { presentationId: presentationId.value },
	})
}

const handleAutoSave = () => {
	if (activeElementIds.value.length || focusElementId.value != null) return
	saveChanges()
}

const changeSlide = async (index, updateCurrent = true) => {
	if (index < 0 || index >= presentation.data.slides.length) return

	resetFocus()
	// reset the pan and zoom to capture thumbnail
	slideContainerRef.value.togglePanZoom()

	await nextTick(async () => {
		// update the current slide along with thumbnail
		if (updateCurrent) {
			await saveChanges()
		}
		slideIndex.value = index
		loadSlide()

		// re-enable pan and zoom
		slideContainerRef.value.togglePanZoom()
	})
}

const performSlideAction = async (action, index) => {
	let url = ''

	switch (action) {
		case 'insert':
			url = 'slides.slides.doctype.presentation.presentation.insert_slide'
			break
		case 'duplicate':
			url = 'slides.slides.doctype.presentation.presentation.duplicate_slide'
			break
		case 'delete':
			url = 'slides.slides.doctype.presentation.presentation.delete_slide'
			break
	}

	const args = {
		name: presentationId.value,
		index: index,
	}

	resetFocus()

	// make sure nextTick call completes before completing the action
	// to ensure slide index is not updated before the action is completed
	await nextTick(async () => {
		await saveChanges()
		await call(url, args)
		await presentation.reload()
	})
}

const insertSlide = async (index) => {
	if (!index) index = slideIndex.value
	const previousBackground = slide.value.background
	await performSlideAction('insert', index)
	await changeSlide(index + 1)
	slide.value.background = previousBackground
	nextTick(() => {
		updateSlideThumbnail()
	})
}

const deleteSlide = async () => {
	if (presentation.data.slides.length == 1) {
		slide.value = {
			...slide.value,
			thumbnail: '',
			elements: [],
			background: '',
			transition: '',
			transitionDuration: 0,
		}
		return
	}
	await performSlideAction('delete', slideIndex.value)
	if (slideIndex.value == presentation.data.slides.length)
		changeSlide(slideIndex.value - 1, false)
	else loadSlide()
}

const duplicateSlide = async (e) => {
	e.preventDefault()
	await performSlideAction('duplicate', slideIndex.value)
	changeSlide(slideIndex.value + 1)
}

const resetAndSave = () => {
	resetFocus()
	nextTick(() => {
		const toastProps = {
			loading: `Saving ...`,
			success: () => `Saved`,
			error: () => 'Could not save presentation. Please try again.',
		}
		toast.promise(saveChanges(), toastProps)
	})
}

const resetSlideState = () => {
	slideIndex.value = 0
	slide.value = {
		thumbnail: '',
		elements: [],
		background: '',
		transition: '',
		transitionDuration: 0,
	}
}

watch(
	() => route.params.presentationId,
	(id) => {
		if (!id) return
		loadPresentation(id)
	},
	{ immediate: true },
)

onMounted(() => {
	autosaveInterval = setInterval(handleAutoSave, 2000)
	document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	clearInterval(autosaveInterval)
	resetFocus()
	document.removeEventListener('keydown', handleKeyDown)
})

onBeforeRouteLeave((to, from, next) => {
	if (to.name !== 'Slideshow') {
		resetSlideState()
	}
	next()
})
</script>
