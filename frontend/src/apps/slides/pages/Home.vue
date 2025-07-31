<template>
	<div class="fixed flex h-screen w-screen flex-col">
		<Navbar
			:primaryButton="{
				label: 'New',
				icon: Plus,
				onClick: () => openThemeDialog(),
			}"
		/>

		<PresentationList
			:presentations="presentationList.data"
			@setPreview="setPreview"
			@navigate="(name, present) => navigateToPresentation(name, present)"
			@openDialog="openDialog"
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
		:presentation="selectedPresentation"
		@reloadList="reloadList"
		@closeDialog="closeDialog"
		@navigate="navigateToPresentation"
	/>

	<ThemeDialog v-model="showThemeDialog" @create="(theme) => createPresentation(theme)" />
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
import ThemeDialog from '@/components/ThemeDialog.vue'

import { createPresentationResource } from '@/stores/presentation'

const router = useRouter()

const previewPresentation = ref(null)
const selectedPresentation = ref(null)

const showDialog = ref(false)
const showThemeDialog = ref(false)
const dialogAction = ref('')

const presentationList = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_all_presentations',
	method: 'GET',
	auto: true,
})

const navigateToPresentation = (name, present) => {
	name = name || previewPresentation.value?.name
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

const openDialog = (action, presentation) => {
	dialogAction.value = action
	showDialog.value = true
	selectedPresentation.value = presentation || previewPresentation.value
}

const closeDialog = () => {
	showDialog.value = false
}

const reloadList = async () => {
	await presentationList.reload()
	previewPresentation.value = null
}

const setPreview = (presentation) => {
	previewPresentation.value = presentation
}

const createPresentation = async (theme) => {
	showThemeDialog.value = false
	const newPresentation = await createPresentationResource.submit({
		title: 'Untitled',
		theme: theme,
	})
	if (newPresentation) {
		navigateToPresentation(newPresentation)
	} else {
		console.error('Failed to create new presentation')
	}
}

const openThemeDialog = () => {
	showThemeDialog.value = true
}
</script>
