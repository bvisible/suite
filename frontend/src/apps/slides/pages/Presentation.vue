<template>
	<div
		ref="parent"
		class="fixed flex h-screen w-screen flex-col select-none"
		:class="!activeElementIds.length ? 'bg-gray-200' : 'bg-gray-50'"
		@dragenter.prevent="handleDragEnter"
		@dragleave.prevent="handleDragLeave"
		@dragover.prevent
		@drop="handleMediaDrop"
	>
		<!-- Navbar -->
		<div
			class="z-10 flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-300"
			@wheel.prevent="(e) => e.stopPropagation()"
		>
			<div class="flex items-center gap-2">
				<img src="../icons/slides.svg" class="h-7" />
				<div class="select-none font-semibold">Slides</div>
			</div>

			<div class="flex justify-center items-center">
				<input
					spellcheck="false"
					ref="newTitleRef"
					v-if="renameMode"
					class="max-w-42 rounded-sm border-none py-1 text-base font-semibold text-gray-700 focus:ring-2 focus:ring-gray-400 focus:ring-offset-1"
					v-model="newTitle"
					@blur="saveTitle"
				/>
				<span
					v-else
					class="select-none font-semibold text-gray-700"
					@click="enableRenameMode"
				>
					{{ presentation.data?.title }}
				</span>
				<span class="text-gray-500"
					>&nbsp;&#8729;&nbsp;{{ slideDirty ? 'Unsaved' : 'Saved' }}</span
				>
			</div>

			<div class="flex items-center gap-2 justify-end">
				<Button
					size="sm"
					:variant="'subtle'"
					:loading="saving"
					:disabled="!slideDirty"
					@click="saveChanges"
				>
					<template #icon>
						<FeatherIcon name="save" class="h-3.5" />
					</template>
				</Button>
				<Button
					variant="solid"
					label="Present"
					size="sm"
					@click="router.replace({ query: { present: true } })"
				>
					<template #prefix>
						<Presentation size="14" class="text-white stroke-[1.5]" />
					</template>
				</Button>
			</div>
		</div>

		<div v-if="presentation.data?.slides" class="flex h-full items-center justify-center">
			<SlideNavigationPanel :showNavigator="showNavigator" />

			<div
				ref="slideContainer"
				class="slideContainer flex items-center justify-center w-full h-full"
				:style="containerStyles"
			>
				<Slide
					v-if="slideContainerRef"
					ref="slide"
					:containerRef="slideContainerRef"
					:class="{
						'outline outline-1.5 outline-blue-400': isMediaDragOver,
					}"
				/>

				<!-- Media Drag Overlay -->
				<div
					v-show="isMediaDragOver"
					class="bg-blue-400 opacity-10 z-15 w-full h-full fixed top-0 left-0"
				></div>
			</div>

			<SlideElementsPanel />
		</div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick, useTemplateRef, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { toast } from 'vue-sonner'

import { call, FileUploadHandler, Spinner } from 'frappe-ui'

import { Presentation } from 'lucide-vue-next'
import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import Slide from '@/components/Slide.vue'

import { presentationId, presentation, inSlideShow } from '@/stores/presentation'
import {
	slideIndex,
	slideDirty,
	saving,
	slideFocus,
	saveChanges,
	duplicateSlide,
	deleteSlide,
	changeSlide,
} from '@/stores/slide'
import {
	activePosition,
	resetFocus,
	activeElementIds,
	focusElementId,
	deleteElements,
	duplicateElements,
	addTextElement,
	addMediaElement,
	selectAllElements,
} from '@/stores/element'

let autosaveInterval = null

const route = useRoute()
const router = useRouter()

const slideRef = useTemplateRef('slide')
const parentRef = useTemplateRef('parent')
const slideContainerRef = useTemplateRef('slideContainer')
const newTitleRef = useTemplateRef('newTitleRef')

const newTitle = ref('')
const renameMode = ref(false)
const showNavigator = ref(true)
const isMediaDragOver = ref(false)

const containerStyles = computed(() => {
	if (!inSlideShow.value) return {}
	return {
		clipPath: 'inset(45px 0 45px 0)',
		backgroundColor: 'black',
	}
})

const enableRenameMode = () => {
	renameMode.value = true
	newTitle.value = presentation.data.title
	nextTick(() => newTitleRef.value.focus())
}

const saveTitle = async () => {
	if (newTitle.value && newTitle.value != presentation.data.title) {
		let nameSlug = await call(
			'slides.slides.doctype.presentation.presentation.rename_presentation',
			{
				name: route.params.presentationId,
				new_name: newTitle.value,
			},
		)
		await router.replace({ name: 'Presentation', params: { presentationId: nameSlug } })
	}
	renameMode.value = false
}

const handleElementShortcuts = (e) => {
	switch (e.key) {
		case 'ArrowLeft':
		case 'ArrowRight':
		case 'ArrowUp':
		case 'ArrowDown':
			slideRef.value.guides.handleArrowKeys(e.key)
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
	if (!parentRef.value.contains(e.relatedTarget)) {
		isMediaDragOver.value = false
	}
}

const handleMediaDrop = async (e) => {
	e.preventDefault()
	isMediaDragOver.value = false
	const files = e.dataTransfer.files
	const fileUploadHandler = new FileUploadHandler()
	files.forEach((file, index) => {
		const fileType = file.type.split('/')[0]
		if (['image', 'video'].includes(fileType)) {
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
		}
	})
}

const startSlideShow = async () => {
	await saveChanges()
	await presentation.reload()
	await changeSlide(0)

	const elem = slideContainerRef.value

	if (elem.requestFullscreen) {
		elem.requestFullscreen()
	} else if (elem.webkitRequestFullscreen) {
		elem.webkitRequestFullscreen()
	} else if (elem.msRequestFullscreen) {
		elem.msRequestFullscreen()
	}
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

watch(
	() => route.query.present,
	async (present) => {
		present && (await startSlideShow())
		inSlideShow.value = present
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
