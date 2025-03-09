<template>
	<div class="fixed flex flex-col h-screen w-screen">
		<Navbar
			:primaryButton="{
				label: 'New',
				icon: Plus,
				onClick: () => openDialog('Create'),
			}"
		/>

		<PresentationList
			:presentations="presentationList.data"
			:blur="previewPresentation != undefined"
			@setPreview="setPreview"
		/>

		<PresentationPreview
			:presentation="previewPresentation"
			@setPreview="setPreview"
			@openDialog="openDialog"
			@navigate="navigateToPresentation"
		/>
	</div>

	<PresentationActionDialog
		v-model="showDialog"
		:dialogAction="dialogAction"
		:presentationTitle="previewPresentation?.title || ''"
		@delete="deletePresentation"
		@create="(title) => addPresentation(title)"
		@duplicate="(title) => addPresentation(title, true)"
	/>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'

import { createResource, call } from 'frappe-ui'

import { Plus } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationList from '@/components/PresentationList.vue'
import PresentationPreview from '@/components/PresentationPreview.vue'
import PresentationActionDialog from '@/components/PresentationActionDialog.vue'

const router = useRouter()

const previewPresentation = ref(null)

const showDialog = ref(false)
const dialogAction = ref('')

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const navigateToPresentation = async (name, present) => {
	name = name || previewPresentation.value.name
	await router.replace({
		name: 'Presentation',
		params: { presentationId: name },
		query: { present: present },
	})
}

const createPresentationDoc = async (title, duplicateFrom) => {
	return await call('slides.slides.doctype.presentation.presentation.create_presentation', {
		title: title,
		duplicate_from: duplicateFrom,
	})
}

const addPresentation = async (title, duplicate) => {
	closeDialog()
	const presentation = await createPresentationDoc(
		title,
		duplicate ? previewPresentation.value.name : null,
	)
	navigateToPresentation(presentation.name)
}

const deletePresentation = async () => {
	closeDialog()
	await call('slides.slides.doctype.presentation.presentation.delete_presentation', {
		name: previewPresentation.value.name,
	})
	await presentationList.reload()
	previewPresentation.value = null
}

const openDialog = (action) => {
	dialogAction.value = action
	showDialog.value = true
}

const closeDialog = () => {
	showDialog.value = false
}

const setPreview = (presentation) => {
	previewPresentation.value = presentation
}
</script>
