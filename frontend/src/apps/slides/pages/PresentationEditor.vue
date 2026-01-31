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

import { initHistory, recentlyRestored } from '@/stores/history'
import {
	presentationId,
	initPresentationDoc,
	presentationDoc,
	unsyncedPresentationRecord,
	slidesLength,
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
	!readonlyMode.value && initHistory()
	presentationDoc.value = await initPresentationDoc(id, readonlyMode.value)
	setSlideIndex(props.activeSlideId)
	updateRoute(presentationDoc.value.slug)
	!readonlyMode.value && initIntervals()
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
	loadPresentation(id)
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
