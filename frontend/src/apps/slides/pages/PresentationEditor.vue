<template>
	<div
		ref="mediaDropContainer"
		class="fixed flex h-screen w-screen flex-col select-none"
		:class="!activeElementIds.length ? 'bg-gray-200' : 'bg-gray-50'"
		@dragenter.prevent="handleDragEnter"
		@dragleave.prevent="handleDragLeave"
		@dragover.prevent
		@drop="handleMediaDrop"
	>
		<Navbar :primaryButton="primaryButtonProps">
			<template #default>
				<PresentationHeader />
			</template>

			<template #actions>
				<Button :loading="saving" :disabled="!slideDirty" @click="saveChanges">
					<template #icon>
						<Save size="14" class="stroke-[1.5]" />
					</template>
				</Button>
			</template>
		</Navbar>

		<div v-if="presentation.data?.slides" class="flex h-full items-center justify-center">
			<SlideNavigationPanel :showNavigator="showNavigator" />

			<SlideContainer :highlight="isMediaDragOver" />

			<SlideElementsPanel />
		</div>
	</div>
</template>

<script setup>
import { ref, watch, useTemplateRef, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { FileUploadHandler } from 'frappe-ui'

import { Presentation, Save } from 'lucide-vue-next'

import Navbar from '@/components/Navbar.vue'
import PresentationHeader from '@/components/PresentationHeader.vue'
import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import SlideContainer from '@/components/SlideContainer.vue'

import { presentationId, presentation } from '@/stores/presentation'
import {
	slideIndex,
	slideDirty,
	saving,
	saveChanges,
	duplicateSlide,
	deleteSlide,
	changeSlide,
} from '@/stores/slide'
import {
	resetFocus,
	activeElementIds,
	focusElementId,
	deleteElements,
	duplicateElements,
	addTextElement,
	addMediaElement,
	selectAllElements,
	activePosition,
} from '@/stores/element'

let autosaveInterval = null

const primaryButtonProps = {
	label: 'Present',
	icon: Presentation,
	onClick: () => startSlideShow(),
}

const route = useRoute()
const router = useRouter()

const slideRef = useTemplateRef('slide')
const mediaDropContainerRef = useTemplateRef('mediaDropContainer')

const showNavigator = ref(true)
const isMediaDragOver = ref(false)

const handleArrowKeys = (key) => {
	let dx = 0
	let dy = 0

	if (key == 'ArrowLeft') dx = -1
	else if (key == 'ArrowRight') dx = 1
	else if (key == 'ArrowUp') dy = -1
	else if (key == 'ArrowDown') dy = 1

	activePosition.value = {
		left: activePosition.value.left + dx,
		top: activePosition.value.top + dy,
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
			if (e.metaKey) duplicateElements(e)
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
			if (e.metaKey) showNavigator.value = !showNavigator.value
			break
		case 'a':
			if (e.metaKey) selectAllElements()
			break
	}
}

const handleKeyDown = (e) => {
	if (document.activeElement.tagName == 'INPUT' || focusElementId.value != null) return
	handleGlobalShortcuts(e)

	activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

const handleDragEnter = (e) => {
	e.preventDefault()
	isMediaDragOver.value = true
}

const handleDragLeave = (e) => {
	e.preventDefault()
	if (!mediaDropContainerRef.value.contains(e.relatedTarget)) {
		isMediaDragOver.value = false
	}
}

const fileUploadHandler = new FileUploadHandler()

const uploadFiles = (files) => {
	files.forEach((file, index) => {
		const fileType = file.type.split('/')[0]
		if (!['image', 'video'].includes(fileType)) return

		setTimeout(() => {
			toast.promise(
				fileUploadHandler.upload(file, { private: false }).then((fileDoc) => {
					addMediaElement(fileDoc, fileType)
				}),
				{
					loading: `Uploading (${index + 1}/${files.length}): ${file.name}`,
					success: (data) => `Uploaded: ${file.name}`,
					error: (data) => 'Upload failed. Please try again.',
				},
			)
		}, 100)
	})
}

const handleMediaDrop = async (e) => {
	e.preventDefault()
	isMediaDragOver.value = false
	const files = e.dataTransfer.files
	uploadFiles(files)
}

const startSlideShow = async () => {
	await saveChanges()
	await presentation.reload()
	router.replace({
		name: 'Slideshow',
		params: { presentationId: presentationId.value },
		query: { present: true },
	})
}

watch(
	() => route.params.presentationId,
	async (id) => {
		if (!id) return
		presentationId.value = id
		await presentation.fetch()
	},
	{ immediate: true },
)

const handleAutoSave = () => {
	if (activeElementIds.value.length) return
	saveChanges()
}

onMounted(() => {
	autosaveInterval = setInterval(handleAutoSave, 60000)
	document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	clearInterval(autosaveInterval)
	document.removeEventListener('keydown', handleKeyDown)
})
</script>
