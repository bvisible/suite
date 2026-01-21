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
			@navigate="(name, present) => navigateToPresentation(name, present)"
			@openDialog="openDialog"
			@duplicatePresentation="(name) => duplicatePresentation(name)"
		/>

		<PresentationPreview
			v-if="previewPresentation"
			:presentation="previewPresentation"
			@setPreview="setPreview"
			@openDialog="openDialog"
			@navigate="navigateToPresentation"
			@duplicatePresentation="(name) => duplicatePresentation(name)"
		/>
	</div>

	<PresentationActionDialog
		v-model="showDialog"
		:dialogAction="dialogAction"
		:presentation="selectedPresentation"
		@reloadList="reloadList"
		@closeDialog="closeDialog"
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

import { createPresentationResource, unsyncedPresentationRecord } from '@/stores/presentation'

const router = useRouter()

const previewPresentation = ref(null)
const selectedPresentation = ref(null)

const showDialog = ref(false)
const dialogAction = ref('')

const presentationList = ref([])
const templateList = ref([])

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
	if (present) {
		router.replace({
			name: 'Slideshow',
			params: { presentationId: name },
			query: { slide: 1 },
		})
	} else {
		reloadList()
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

const reloadList = async () => {
	await presentationListResource.reload()
	previewPresentation.value = null
}

const setPreview = (presentation) => {
	previewPresentation.value = presentation
}

const createPresentation = async (template) => {
	if (!template) {
		template = templateList.value.find((t) => t.title === 'Light')?.name
	}
	const newPresentation = await createPresentationResource.submit({
		template: template,
	})
	if (newPresentation) {
		navigateToPresentation(newPresentation)
	} else {
		console.error('Failed to create new presentation')
	}
}

const duplicatePresentation = async (presentation) => {
	const newPresentation = await createPresentationResource.submit({
		duplicateFrom: presentation,
	})
	if (newPresentation) {
		navigateToPresentation(newPresentation)
	} else {
		console.error('Failed to create new presentation')
	}
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
