<template>
	<div class="flex h-screen w-screen select-none flex-col overflow-hidden">
		<Navbar :primaryButton="primaryButtonProps">
			<template #default>
				<PresentationHeader />
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
				@changeSlide="changeSlide"
				@openLayoutDialog="openLayoutDialog('insert')"
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
			v-if="presentation.data"
			v-model="showLayoutDialog"
			:theme="presentation.data.theme"
			@insert="(layoutId) => handleInsertSlide(layoutId)"
		/>
	</div>
</template>

<script setup>
import { ref, watch, computed, useTemplateRef, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'

import { call, toast } from 'frappe-ui'

import { Presentation } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import Toolbar from '@/components/Toolbar.vue'
import LayoutDialog from '@/components/LayoutDialog.vue'

import { presentationId, presentation } from '@/stores/presentation'
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
	deleteAttachments,
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
	if (hasOngoingInteraction.value || focusElementId.value != null) return
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

const performSlideAction = async (action, index, layoutId) => {
	if (!index) index = slideIndex.value
	let url = ''

	switch (action) {
		case 'insert':
			url = 'slides.slides.doctype.presentation.presentation.insert_slide'
			break
		case 'duplicate':
			url = 'slides.slides.doctype.presentation.presentation.duplicate_slide'
			break
		case 'replace':
			url = 'slides.slides.doctype.presentation.presentation.insert_slide'
			break
		case 'delete':
			url = 'slides.slides.doctype.presentation.presentation.delete_slide'
			break
	}

	const args = {
		name: presentationId.value,
		index: index,
		layout_id: layoutId,
		replace: action == 'replace',
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

const insertSlide = async (index, layoutId) => {
	if (!index) index = slideIndex.value
	const previousBackground = slide.value.background
	await performSlideAction('insert', index, layoutId)
	await changeSlide(index + 1)
	slide.value.background = previousBackground
	nextTick(() => {
		updateSlideThumbnail()
	})
}

const loadSlidePostDeletion = async (index) => {
	// if last slide is deleted, load the previous slide
	if (slideIndex.value == presentation.data.slides.length)
		changeSlide(slideIndex.value - 1, false)
	// otherwise load next one
	else loadSlide()
}

const deleteSlide = async () => {
	// store elements to delete attachments later
	const elements = slide.value.elements

	// if there is only one slide, reset the slide state instead of deleting
	if (presentation.data.slides.length == 1) return resetSlideState()

	await performSlideAction('delete')
	loadSlidePostDeletion()

	deleteAttachments(elements)
}

const duplicateSlide = async (e) => {
	e.preventDefault()
	await performSlideAction('duplicate')
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
	slide.value = {
		thumbnail: '',
		elements: [],
		background: '',
		transition: '',
		transitionDuration: '0',
	}
}

const addRouteSlug = async () => {
	const slug = presentation.data.slug
	if (route.params.slug === slug) return
	router.replace({
		name: 'PresentationEditor',
		params: { presentationId: presentationId.value, slug: slug },
	})
}

watch(
	() => route.params.presentationId,
	async (id) => {
		if (!id) return
		presentationId.value = id
		await presentation.fetch()
		addRouteSlug()
		loadSlide()
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
		slideIndex.value = 0
		resetSlideState()
		presentationId.value = ''
		presentation.reset()
	}
	next()
})

const showLayoutDialog = ref(false)
const layoutAction = ref('')

const openLayoutDialog = (action) => {
	showLayoutDialog.value = true
	layoutAction.value = action
}

const handleInsertSlide = async (layoutId) => {
	if (layoutAction.value == 'replace') {
		await performSlideAction('replace', slideIndex.value, layoutId)
		loadSlide()
	} else {
		insertSlide(null, layoutId)
	}
}
</script>
