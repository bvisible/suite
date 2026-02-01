<template>
	<div
		class="flex h-screen w-screen select-none flex-col overflow-hidden"
		@click="focusedSlide = null"
	>
		<EditorNavbar @startSlideShow="startSlideShow()" />

		<div class="relative flex h-screen bg-gray-300">
			<SlideContainer
				ref="slideContainer"
				v-if="presentationDoc"
				:highlight="slideHighlight"
				v-model:hasOngoingInteraction="hasOngoingInteraction"
				@changeSlide="changeEditorSlide"
			/>

			<NavigationPanel
				class="absolute bottom-0 top-0"
				:recentlyRestored="recentlyRestored"
				@changeSlide="changeEditorSlide"
				@addEmptySlide="addEmptySlide(null, slidesLength - 1)"
			/>

			<Toolbar
				v-if="!inReadonlyMode"
				@setHighlight="setHighlight"
				@toggleLayoutView="toggleLayoutView"
				@addEmptySlide="addEmptySlide"
				@duplicate="duplicateSlide"
				@delete="deleteSlide(true)"
			/>

			<PropertiesPanel
				v-if="!inReadonlyMode"
				class="absolute bottom-0 right-0 top-0"
				:showLayoutsView="showLayoutsView"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, useTemplateRef, provide, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'

import EditorNavbar from '@/components/EditorNavbar.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import Toolbar from '@/components/Toolbar.vue'

import { initHistory, recentlyRestored } from '@/stores/history'
import {
	presentationId,
	initPresentationDoc,
	presentationDoc,
	unsyncedPresentationRecord,
	slidesLength,
	templateList,
	templateListResource,
	inReadonlyMode,
	showLayoutsView,
} from '@/stores/presentation'
import {
	slides,
	slideIndex,
	selectionBounds,
	updateThumbnail,
	lastThumbnailTime,
	focusedSlide,
	setSlideIndex,
	changeEditorSlide,
	deleteSlide,
	duplicateSlide,
	addEmptySlide,
} from '@/stores/slide'
import { resetFocus, focusElementId } from '@/stores/element'

import { useShortcuts } from '@/composables/useShortcuts'
import {
	saveChanges,
	dirtySince,
	isDirty,
	syncPresentationToServer,
	syncThumbnail,
} from '@/stores/saving'
import { inSlideShowMode, startSlideShow } from '@/stores/slideshow'

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
useShortcuts(inReadonlyMode, inSlideShowMode)

const layoutAction = ref('')
const slideHighlight = ref(false)
const hasOngoingInteraction = ref(false)

const setHighlight = (value) => {
	slideHighlight.value = value
}

const toggleLayoutView = () => {
	showLayoutsView.value = !showLayoutsView.value
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
	presentationDoc.value = await initPresentationDoc(id, inReadonlyMode.value)
}

const updateUnsyncedRecord = () => {
	unsyncedPresentationRecord.value = {
		...unsyncedPresentationRecord.value,
		modified: presentationDoc.value.modified,
		thumbnail: slides.value[0]?.thumbnail,
	}
}

const handleBeforeUnload = (e) => {
	if (isDirty.value || syncThumbnail > 0) {
		e.preventDefault()
		e.returnValue = ''
	}
}

const loadTemplates = () => {
	if (templateList.value.length || inReadonlyMode.value) return
	templateListResource.fetch()
}

const performBeforeLoadOperations = () => {
	if (inReadonlyMode.value) return

	window.addEventListener('beforeunload', handleBeforeUnload)

	initHistory()
}

const performAfterLoadOperations = () => {
	setSlideIndex(props.activeSlideId)
	updateRoute(presentationDoc.value.slug)

	if (inReadonlyMode.value) return

	initIntervals()
}

const handleMounted = async () => {
	loadTemplates()

	const id = props.presentationId
	if (!id) return

	performBeforeLoadOperations()
	await loadPresentation(id)
	performAfterLoadOperations()
}

const handleBeforeUnmount = () => {
	updateUnsyncedRecord()
	clearInterval(autosaveInterval)
	clearInterval(thumbnailInterval)

	if (router.currentRoute.value.name !== 'Slideshow') {
		resetFocus()
		syncPresentationToServer()
	}
	window.removeEventListener('beforeunload', handleBeforeUnload)
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

watch(
	() => props.editorAccess,
	(doc) => {
		inReadonlyMode.value = doc === 'view'
	},
)

onMounted(() => handleMounted())

onBeforeUnmount(() => handleBeforeUnmount())

provide('inReadonlyMode', inReadonlyMode)
provide('inSlideShowMode', inSlideShowMode)
</script>
