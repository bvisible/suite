<template>
	<div class="flex h-screen w-screen flex-col">
		<Navbar
			:primaryButton="{
				label: 'New',
				icon: Plus,
				onClick: () => createPresentation(),
			}"
		/>

		<PresentationList
			:loading="presentationListResource.loading"
			:presentations="presentationList"
			@setPreview="setPreview"
			@navigate="navigateToPresentation"
			@openDialog="openDialog"
			@duplicatePresentation="duplicatePresentation"
		/>

		<PresentationPreview
			v-if="previewPresentation"
			:presentation="previewPresentation"
			@setPreview="setPreview"
			@openDialog="openDialog"
			@navigate="navigateToPresentation"
			@duplicatePresentation="duplicatePresentation"
		/>
	</div>

	<PresentationActionDialog
		v-model="showDialog"
		:dialogAction="dialogAction"
		:presentation="selectedPresentation"
		@closeDialog="closeDialog"
		@updatePresentationList="updatePresentationList"
	/>
</template>

<script setup>
import { onActivated, ref } from 'vue'
import { useRouter } from 'vue-router'
import { previousRoute } from '@/router'

import { createResource } from 'frappe-ui'

import { Plus } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationList from '@/components/PresentationList.vue'
import PresentationPreview from '@/components/PresentationPreview.vue'
import PresentationActionDialog from '@/components/PresentationActionDialog.vue'

import {
	createPresentationResource,
	unsyncedPresentationRecord,
	templateList,
} from '@/stores/presentation'

const router = useRouter()

const previewPresentation = ref(null)
const selectedPresentation = ref(null)

const showDialog = ref(false)
const dialogAction = ref('')

const presentationList = ref([])

const presentationListResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentations',
	method: 'GET',
	auto: true,
	cache: 'presentations',
	onSuccess: (data) => {
		presentationList.value = data
	},
})

const templateListResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_templates',
	method: 'GET',
	auto: true,
	cache: 'templates',
	onSuccess: (data) => {
		templateList.value = data
	},
})

const navigateToPresentation = (name, present) => {
	name = name || previewPresentation.value?.name
	previewPresentation.value = null
	if (present) {
		router.replace({
			name: 'Slideshow',
			params: { presentationId: name },
			query: { slide: 1 },
		})
	} else {
		router.push({
			name: 'PresentationEditor',
			params: { presentationId: name },
			query: { slide: 1 },
		})
	}
}

const openDialog = (action, presentation) => {
	dialogAction.value = action
	showDialog.value = true
	selectedPresentation.value = presentation || previewPresentation.value
}

const closeDialog = () => {
	showDialog.value = false
}

const updatePresentationList = (action, newTitle) => {
	if (action == 'Delete') {
		previewPresentation.value = null
		presentationList.value = presentationList.value.filter(
			(p) => p.name !== selectedPresentation.value.name,
		)
	} else if (action == 'Rename' && newTitle) {
		selectedPresentation.value.title = newTitle
	}
}

const setPreview = (presentation) => {
	previewPresentation.value = presentation
}

const createPresentation = async (template) => {
	template = template || templateList.value.find((t) => t.title === 'Light')?.name
	const newPresentation = await createPresentationResource.submit({ template })
	presentationList.value.unshift(newPresentation)
	navigateToPresentation(newPresentation?.name)
}

const duplicatePresentation = async (duplicateFrom) => {
	const newPresentation = await createPresentationResource.submit({ duplicateFrom })
	presentationList.value.unshift(newPresentation)
	navigateToPresentation(newPresentation?.name)
}

const syncPresentationRecord = () => {
	const presentationRecord = presentationList.value.find(
		(p) => p.name == previousRoute.params.presentationId,
	)
	if (!presentationRecord) return

	const newValues = unsyncedPresentationRecord.value

	Object.entries(newValues).forEach(([key, val]) => {
		if (![null, undefined, ''].includes(val)) {
			presentationRecord[key] = val
		}
	})
}

onActivated(() => {
	if (previousRoute?.name == 'PresentationEditor') {
		syncPresentationRecord()
	}
})
</script>
