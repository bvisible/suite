<template>
	<div
		ref="mediaDropContainer"
		class="fixed flex h-screen w-screen flex-col select-none"
		:class="!activeElementIds.length ? 'bg-gray-200' : 'bg-gray-50'"
	>
		<Navbar :primaryButton="primaryButtonProps">
			<template #default>
				<PresentationHeader />
			</template>
		</Navbar>

		<div v-if="presentation.data?.slides" class="flex h-full items-center justify-center">
			<SlideNavigationPanel
				:showNavigator="showNavigator"
				@changeSlide="changeSlide"
				@insertSlide="insertSlide"
			/>

			<SlideContainer
				ref="slideContainer"
				:highlight="highlightSlide"
				@dragenter="handleMediaDragEnter"
			/>

			<DropTargetOverlay ref="dropTarget" />

			<SlideElementsPanel />

			<Toolbar
				@setHighlight="setHighlight"
				@insert="insertSlide"
				@duplicate="duplicateSlide"
				@delete="deleteSlide"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, computed, useTemplateRef, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { call } from 'frappe-ui'

import { Presentation, Save } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import DropTargetOverlay from '@/components/DropTargetOverlay.vue'
import Toolbar from '@/components/Toolbar.vue'

import { presentationId, presentation } from '@/stores/presentation'
import { slide, slideIndex, saveChanges, loadSlide } from '@/stores/slide'
import {
	resetFocus,
	activeElementIds,
	activeElement,
	focusElementId,
	deleteElements,
	duplicateElements,
	addTextElement,
	selectAllElements,
	activePosition,
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
const showHighlight = ref(false)

const highlightSlide = computed(() => {
	return dropTargetRef.value?.isMediaDragOver || showHighlight.value
})

const setHighlight = (value) => {
	showHighlight.value = value
}

const handleArrowKeys = (key) => {
	let dx = 0
	let dy = 0

	if (key == 'ArrowLeft') dx = -1
	else if (key == 'ArrowRight') dx = 1
	else if (key == 'ArrowUp') dy = -1
	else if (key == 'ArrowDown') dy = 1

	slideContainerRef.value.applyMovement({ dx, dy })
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
			if (e.metaKey) duplicateElements(e, activeElements.value)
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
	if (document.activeElement.tagName == 'INPUT' || focusElementId.value != null) return
	handleGlobalShortcuts(e)

	activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

const startSlideShow = () => {
	resetAndSave()

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

	nextTick(async () => {
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
	await performSlideAction('insert', index)
	changeSlide(index + 1)
}

const deleteSlide = async () => {
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
		saveChanges()
	})
}

const handleMediaDragEnter = (e) => {
	e.preventDefault()
	dropTargetRef.value.handleDragEnter(e)
}

watch(
	() => route.params.presentationId,
	(id) => {
		if (!id) return
		presentationId.value = id
	},
	{ immediate: true },
)

onMounted(() => {
	autosaveInterval = setInterval(handleAutoSave, 60000)
	document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	clearInterval(autosaveInterval)
	resetFocus()
	document.removeEventListener('keydown', handleKeyDown)
})
</script>
