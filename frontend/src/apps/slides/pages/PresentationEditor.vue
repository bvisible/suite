<template>
	<div
		class="flex h-screen w-screen select-none flex-col overflow-hidden"
		@click="focusedSlide = null"
	>
		<EditorNavbar
			@startSlideShow="startSlideShow"
			@performDropdownAction="performNavbarDropdownAction"
		/>

		<div class="relative flex h-screen bg-gray-300">
			<SlideContainer
				ref="slideContainer"
				v-if="presentationDoc"
				:highlight="slideHighlight"
				v-model:hasOngoingInteraction="hasOngoingInteraction"
			/>

			<NavigationPanel
				class="absolute bottom-0 top-0"
				@changeSlide="changeEditorSlide"
				@openLayoutDialog="openLayoutDialog('insert')"
			/>

			<Toolbar
				v-if="!inReadonlyMode && presentationDoc"
				@setHighlight="setHighlight"
				@openLayoutDialog="openLayoutDialog('insert')"
				@duplicate="duplicateSlide"
				@delete="deleteSlide(true)"
			/>

			<PropertiesPanel
				v-if="!inReadonlyMode"
				class="absolute bottom-0 right-0 top-0"
				@openLayoutDialog="openLayoutDialog('replace')"
			/>
		</div>
	</div>

	<LayoutDialog
		v-model="showLayoutDialog"
		@insert="(layoutObj) => handleInsertSlide(null, layoutObj)"
	/>

	<ThemeDialog
		v-model="showThemeDialog"
		@create="(theme) => createPresentation(theme)"
		@update="(theme) => updatePresentationTheme(theme)"
		:update="themeDialogAction == 'update'"
	/>

	<teleport to="body">
		<ExportView v-if="showExportView" :slides="slides" />
	</teleport>
</template>

<script setup>
import {
	ref,
	watch,
	useTemplateRef,
	onMounted,
	onBeforeUnmount,
	provide,
	inject,
	nextTick,
} from 'vue'
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router'

import { call, usePageMeta } from 'frappe-ui'

import ExportView from '@/pages/ExportView.vue'
import EditorNavbar from '@/components/EditorNavbar.vue'
import NavigationPanel from '@/components/NavigationPanel.vue'
import PropertiesPanel from '@/components/PropertiesPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'
import Toolbar from '@/components/Toolbar.vue'
import ThemeDialog from '@/components/ThemeDialog.vue'
import LayoutDialog from '@/components/LayoutDialog.vue'

import {
	presentationId,
	initPresentationDoc,
	presentationDoc,
	unsyncedPresentationRecord,
	templateList,
	templateListResource,
	inReadonlyMode,
	createPresentationResource,
	duplicatePresentation,
	deletePresentation,
	presentationTheme,
	resetEditorState,
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
	handleInsertSlide,
} from '@/stores/slide'
import { resetFocus, focusElementId } from '@/stores/element'
import {
	commandHistory,
	setCommandHistory,
	actions as historyMetaActions,
	actionOrder as historyMetaActionOrder,
} from '@/stores/historyMeta'

import { useShortcuts } from '@/composables/useShortcuts'
import { saveChanges, saveCurrentState, dirtySince, isDirty, syncThumbnail } from '@/stores/saving'
import { inSlideShowMode, startSlideShow } from '@/stores/slideshow'
import { Layout } from 'lucide-vue-next'
import { useCommandHistory } from '@/composables/useCommandHistory'

const isDriveInstalled = inject('isDriveInstalled', false)

const route = useRoute()
const router = useRouter()

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

const showThemeDialog = ref(false)
const themeDialogAction = ref('update')
const slideHighlight = ref(false)
const hasOngoingInteraction = ref(false)

const showLayoutDialog = ref(false)
const layoutAction = ref('')
const insertIndex = ref(null)
const showExportView = ref(false)

const historyMetaForCommandHistory = {
	actions: historyMetaActions,
	actionOrder: historyMetaActionOrder,
}

const commandHistoryInstance = useCommandHistory(slides, historyMetaForCommandHistory)
setCommandHistory(commandHistoryInstance)

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
}

const performAfterLoadOperations = () => {
	setSlideIndex(props.activeSlideId)
	updateRoute(presentationDoc.value.slug)

	if (inReadonlyMode.value) return

	initIntervals()
}

const loadEditorState = async () => {
	const id = props.presentationId
	if (!id) return

	performBeforeLoadOperations()
	await loadPresentation(id)
	performAfterLoadOperations()
}

const handleMounted = () => {
	// templates load from Home.vue
	// but if user lands directly on editor check and load them
	loadTemplates()
}

const hideOpenDialogs = () => {
	showThemeDialog.value = false
	showLayoutDialog.value = false
}

const handleBeforeUnmount = () => {
	updateUnsyncedRecord()
	clearInterval(autosaveInterval)
	clearInterval(thumbnailInterval)

	if (router.currentRoute.value.name !== 'Slideshow') {
		resetFocus()
		saveCurrentState()
	}
	window.removeEventListener('beforeunload', handleBeforeUnload)
	window.removeEventListener('popstate', hideOpenDialogs)
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
	() => route.name,
	(name) => {
		if (!['EditorNew', 'PresentationEditor'].includes(name)) return
		inReadonlyMode.value = props.editorAccess == 'view'
		if (name === 'EditorNew') {
			resetEditorState()
			themeDialogAction.value = 'create'
			showThemeDialog.value = true
			return
		}
		loadEditorState()
	},
	{ immediate: true },
)

watch(
	() => props.presentationId,
	(id, prevId) => {
		if (!id || !prevId || id === prevId) return
		inReadonlyMode.value = props.editorAccess == 'view'
		commandHistory.clearHistory()
		loadEditorState()
	},
)

onBeforeRouteLeave(() => {
	hideOpenDialogs()
})

window.addEventListener('popstate', hideOpenDialogs)

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

const navigateToPresentation = async (name) => {
	if (route.name === 'EditorNew') {
		await router.replace({
			name: 'PresentationEditor',
			params: { presentationId: name },
			query: { slide: 1 },
		})
	} else {
		await router.push({
			name: 'PresentationEditor',
			params: { presentationId: name },
			query: { slide: 1 },
		})
	}
}

const createPresentation = async (theme) => {
	showThemeDialog.value = false
	const newPresentation = await createPresentationResource.submit({
		template: theme,
	})
	const name = newPresentation?.name

	if (!name) {
		console.error('Failed to create new presentation')
		return
	}

	if (isDriveInstalled) {
		const parent = route.query.parent || ''
		call('slides.api.file.create_drive_file', {
			name: name,
			parent: parent,
		})
	}

	navigateToPresentation(name)
}

const updatePresentationTheme = async (theme) => {
	if (!presentationId.value) return

	showThemeDialog.value = false

	call('frappe.client.set_value', {
		doctype: 'Presentation',
		name: presentationId.value,
		fieldname: 'theme',
		value: theme,
	}).then(() => {
		presentationDoc.value.theme = theme
	})
}

const performNavbarDropdownAction = async (action) => {
	if (action == 'create') {
		await router.push({ name: 'EditorNew' })
	} else if (action == 'duplicate') {
		const newPresentation = await duplicatePresentation(presentationId.value)
		navigateToPresentation(newPresentation)
	} else if (action == 'delete') {
		await deletePresentation(presentationId.value)
		unsyncedPresentationRecord.value = { name: presentationId.value, deleted: true }
		router.push({ name: 'Home' })
	} else if (action == 'updateTheme') {
		themeDialogAction.value = 'update'
		showThemeDialog.value = true
	} else if (action == 'export') {
		exportPdf()
	}
}

const openLayoutDialog = (action, index) => {
	showLayoutDialog.value = true
	layoutAction.value = action
	insertIndex.value = index
}

usePageMeta(() => {
	return {
		title: presentationDoc.value?.title || 'Slides',
	}
})

useShortcuts(inReadonlyMode, inSlideShowMode)

const cleanup = () => {
	showExportView.value = false
	window.removeEventListener('afterprint', cleanup)
}

const exportPdf = () => {
	showExportView.value = true

	nextTick(() => {
		setTimeout(() => {
			window.addEventListener('afterprint', cleanup, { once: true })
			window.print()
		}, 200)
	})
}
</script>
