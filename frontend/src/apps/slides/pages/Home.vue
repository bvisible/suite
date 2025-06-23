<template>
	<div class="fixed flex h-screen w-screen flex-col">
		<Navbar
			:primaryButton="{
				label: 'New',
				icon: Plus,
				onClick: () => createPresentation(),
			}"
		/>

		<PresentationList
			:presentations="presentationList.data"
			:blur="previewPresentation != undefined"
			@setPreview="setPreview"
		/>

		<PresentationPreview
			v-if="previewPresentation"
			:presentation="previewPresentation"
			@setPreview="setPreview"
			@openDialog="openDialog"
			@navigate="navigateToPresentation"
		/>
	</div>

	<PresentationActionDialog
		v-model="showDialog"
		:dialogAction="dialogAction"
		:presentation="previewPresentation"
		@reloadList="reloadList"
		@closeDialog="closeDialog"
		@navigate="navigateToPresentation"
	/>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { createResource } from 'frappe-ui'

import { Plus } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationList from '@/components/PresentationList.vue'
import PresentationPreview from '@/components/PresentationPreview.vue'
import PresentationActionDialog from '@/components/PresentationActionDialog.vue'

import { createPresentationResource } from '@/stores/presentation'

const router = useRouter()

const previewPresentation = ref(null)

const showDialog = ref(false)
const dialogAction = ref('')

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const navigateToPresentation = (name, present) => {
	name = name || previewPresentation.value.name
	if (present) {
		router.replace({
			name: 'Slideshow',
			params: { presentationId: name },
		})
	} else {
		router.push({
			name: 'PresentationEditor',
			params: { presentationId: name },
		})
	}
}

const openDialog = (action) => {
	dialogAction.value = action
	showDialog.value = true
}

const closeDialog = () => {
	showDialog.value = false
}

const reloadList = async () => {
	closeDialog()
	await presentationList.reload()
	previewPresentation.value = null
}

const navigate = (name) => {
	closeDialog()
	navigateToPresentation(name)
}

const setPreview = (presentation) => {
	previewPresentation.value = presentation
}

const createPresentation = async () => {
	const newPresentation = await createPresentationResource.submit({
		title: 'Untitled',
	})
	if (newPresentation) {
		navigateToPresentation(newPresentation.name)
	} else {
		console.error('Failed to create new presentation')
	}
}
</script>
