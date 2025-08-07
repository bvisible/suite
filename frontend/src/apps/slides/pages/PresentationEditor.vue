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
			v-if="presentationDoc"
			v-model="showLayoutDialog"
			:theme="presentationDoc.theme"
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

import { call, toast, createDocumentResource } from 'frappe-ui'

import { Presentation } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import Toolbar from '@/components/Toolbar.vue'
import LayoutDialog from '@/components/LayoutDialog.vue'

import { presentationId } from '@/stores/presentation'
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
			if (e.metaKey) historyControl.undo()
			else if (e.shiftKey) historyControl.redo()
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

const insertSlide = async (index, layoutId) => {
	if (!index) index = slideIndex.value
	await performSlideAction('insert', index, layoutId)
	await changeSlide(index + 1)
}

const loadSlidePostDeletion = async (index) => {
	// if last slide is deleted, load the previous slide
	if (slideIndex.value == slides.value.length) changeSlide(slideIndex.value - 1, false)
}

const deleteSlide = async () => {
	// store elements to delete attachments later
	const elements = currentSlide.value.elements

	// if there is only one slide, reset the slide state instead of deleting
	if (slides.value.length == 1) return resetSlideState()

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

const addRouteSlug = async (slug) => {
	if (props.slug == slug) return
	router.replace({
		name: 'PresentationEditor',
		params: { presentationId: presentationId.value, slug: slug },
	})
}

const parseElements = (value) => {
	if (!value) return []
	if (typeof value === 'string') {
		try {
			return JSON.parse(value)
		} catch {
			return []
		}
	}
	return Array.isArray(value) ? value : []
}

const presentationDoc = ref(null)

const getPresentationResource = (name) => {
	return createDocumentResource({
		doctype: 'Presentation',
		name: name,
		auto: false,
		transform(doc) {
			for (const slide of doc.slides || []) {
				slide.elements = parseElements(slide.elements)
			}
		},
		onSuccess(doc) {
			slides.value = JSON.parse(JSON.stringify(doc.slides || []))

			addRouteSlug(doc.slug)
		},
	})
}

watch(
	() => props.presentationId,
	async (id) => {
		if (!id) return
		presentationId.value = id
		const resource = getPresentationResource(props.presentationId)
		await resource.get.fetch()
		presentationDoc.value = resource.doc
	},
	{ immediate: true },
)

onBeforeRouteLeave((to, from, next) => {
	if (to.name !== 'Slideshow') {
		slideIndex.value = 0
		presentationId.value = ''
	}
	next()
})

onActivated(async () => {
	const resource = getPresentationResource(props.presentationId)
	await resource.get.fetch()
	presentationDoc.value = resource.doc
	// autosaveInterval = setInterval(handleAutoSave, 2000)
	document.addEventListener('keydown', handleKeyDown)
})

onDeactivated(() => {
	clearInterval(autosaveInterval)
	resetFocus()
	document.removeEventListener('keydown', handleKeyDown)
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
	} else {
		insertSlide(null, layoutId)
	}
}

let historyControl

watch(
	() => presentation?.isFinished,
	() => {
		historyControl = useDebouncedRefHistory(slides, {
			deep: true,
			debounce: 2000,
			maxLength: 10,
		})
	},
)

const saveChanges = async () => {}
</script>
