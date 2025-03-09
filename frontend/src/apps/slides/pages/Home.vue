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
		:presentation="previewPresentation"
		@reloadList="reloadList"
		@navigate="navigate"
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
</script>
