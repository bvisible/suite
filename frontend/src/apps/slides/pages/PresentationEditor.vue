<template>
	<div class="flex h-screen w-screen select-none flex-col overflow-hidden">
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
import {
	ref,
	reactive,
	watch,
	computed,
	useTemplateRef,
	onMounted,
	onBeforeUnmount,
	nextTick,
	onDeactivated,
	onActivated,
	shallowRef,
} from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { useDebouncedRefHistory } from '@vueuse/core'

import { call, toast } from 'frappe-ui'

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
	getPresentationResource,
	hasStateChanged,
	savePresentationDoc,
	layoutResource,
	initPresentationDoc,
} from '@/stores/presentation'
import {
	slides,
	slideIndex,
	currentSlide,
	selectionBounds,
	updateSelectionBounds,
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
import { generateUniqueId } from '@/utils/helpers'

let autosaveInterval = null

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => startSlideShow(),
}

const props = defineProps({
	presentationId: String,
	slug: String,
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
		case 'z':
			e.preventDefault()
			if (e.shiftKey && e.metaKey && historyControl?.canRedo) {
				historyControl.redo()
			} else if (e.metaKey && historyControl?.canUndo) {
				historyControl.undo()
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
		params: { presentationId: props.presentationId },
	})
}

const handleAutoSave = () => {
	if (hasOngoingInteraction.value || focusElementId.value != null) return
	saveChanges()
}

const changeSlide = async (index, updateCurrent = true) => {
	if (index < 0 || index >= slides.value.length) return

	resetFocus()
	// reset the pan and zoom to capture thumbnail
	slideContainerRef.value.togglePanZoom()

	await nextTick(async () => {
		// update the current slide along with thumbnail
		if (updateCurrent) {
			await saveChanges()
		}
		slideIndex.value = index

		// re-enable pan and zoom
		slideContainerRef.value.togglePanZoom()
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
		Object.assign(slide, layout)
	}

	// override metadata and generate unique IDs for elements
	slide.name = ''
	slide.parent = presentationId.value
	slide.elements.forEach((element) => {
		element.id = generateUniqueId()
	})

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
	// if there is only one slide, reset the slide state instead of deleting
	const totalLength = slides.value.length

	if (totalLength == 1) {
		slides.value[0].elements = []
		return
	}

	// delete the current slide
	slides.value = slides.value.filter((slide, i) => i != slideIndex.value)
	slides.value.forEach((slide, index) => {
		slide.idx = index + 1
	})

	// if last slide is deleted, switch to previous slide since no slide at current index
	if (slideIndex.value == totalLength) changeSlide(slideIndex.value - 1, false)
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

const addRouteSlug = async (slug) => {
	if (props.slug == slug) return
	router.replace({
		name: 'PresentationEditor',
		params: { presentationId: presentationId.value, slug: slug },
	})
}

const presentationDoc = ref(null)

const initHistory = () => {
	historyControl = useDebouncedRefHistory(slides, {
		deep: true,
		debounce: 2000,
		maxLength: 10,
	})
}

const initAutosave = () => {
	autosaveInterval = setInterval(handleAutoSave, 2000)
}

const loadPresentation = async (id) => {
	presentationDoc.value = await initPresentationDoc(id)
	addRouteSlug(presentationDoc.value.slug)
	layoutResource.fetch({ theme: presentationDoc.value.theme })
	initHistory()
	initAutosave()
	document.addEventListener('keydown', handleKeyDown)
}

onBeforeRouteLeave((to, from, next) => {
	if (to.name !== 'Slideshow') {
		slideIndex.value = 0
		presentationId.value = ''
	}
	next()
})

let historyControl

onActivated(() => {
	const id = props.presentationId
	if (!id) return
	loadPresentation(id)
})

onDeactivated(() => {
	clearInterval(autosaveInterval)
	resetFocus()
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

	const original = presentationDoc.value.slides || []
	const current = slides.value || []

	return hasStateChanged(original, current)
})

const saveChanges = async () => {
	if (!isDirty.value) return

	presentationDoc.value = await savePresentationDoc()
}
</script>
