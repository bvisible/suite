<template>
	<div
		ref="parent"
		class="fixed flex h-screen w-screen flex-col bg-gray-100"
		@dragenter.prevent="handleDragEnter"
		@dragleave.prevent="handleDragLeave"
		@dragover.prevent
		@drop="handleMediaDrop"
	>
		<!-- Navbar -->
		<div class="z-10 flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-300">
			<div class="flex items-center gap-2">
				<img src="../icons/slides.svg" class="h-7" />
				<div class="select-none font-semibold">Slides</div>
			</div>

			<input
				spellcheck="false"
				ref="newTitleRef"
				v-if="renameMode"
				class="max-w-42 rounded-sm border-none py-1 text-base font-semibold text-gray-700 focus:ring-2 focus:ring-gray-400 focus:ring-offset-1"
				v-model="newTitle"
				@blur="saveTitle"
			/>
			<span v-else class="select-none font-semibold text-gray-700" @click="enableRenameMode">
				{{ presentation.data?.title }}
			</span>
			<Button variant="solid" label="Present" size="sm" @click="enablePresentMode" />
		</div>

		<div
			ref="container"
			class="flex h-full items-center justify-center"
			@click="(e) => clearFocus(e)"
		>
			<SlideNavigationPanel :showNavigator="showNavigator" />

			<div
				v-if="containerRef"
				ref="slideContainer"
				class="slideContainer flex items-center justify-center w-[960px] h-[540px]"
				:class="{
					'bg-black': inSlideShow,
					'outline-blue-300 outline': isMediaDragOver,
				}"
			>
				<Slide ref="slide" :containerRef="containerRef" :slideCursor="slideCursor" />

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
import { ref, watch, onMounted, nextTick, useTemplateRef, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { call, FileUploadHandler } from 'frappe-ui'

import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import Slide from '@/components/Slide.vue'

import { presentationId, presentation, inSlideShow, startSlideShow } from '@/stores/presentation'
import {
	slideIndex,
	slideFocus,
	saveChanges,
	duplicateSlide,
	deleteSlide,
	changeSlide,
} from '@/stores/slide'
import {
	activePosition,
	resetFocus,
	activeElementId,
	focusElementId,
	deleteElement,
	duplicateElement,
	addTextElement,
	addMediaElement,
} from '@/stores/element'

let autosaveInterval = null

const route = useRoute()
const router = useRouter()

const parentRef = useTemplateRef('parent')
const containerRef = useTemplateRef('container')
const newTitleRef = useTemplateRef('newTitleRef')

const renameMode = ref(false)
const newTitle = ref('')

const showNavigator = ref(true)

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

const clearFocus = (e) => {
	if (e.target == containerRef.value) {
		resetFocus()
		slideFocus.value = false
	}
}

const enablePresentMode = async () => {
	await saveChanges()
	await presentation.reload()
	await startSlideShow()
}

const updateElementPosition = (dx, dy) => {
	if (!activePosition.value) return
	activePosition.value = {
		left: activePosition.value.left + dx,
		top: activePosition.value.top + dy,
	}
}

const handleArrowKeys = (key) => {
	let dx = 0
	let dy = 0

	if (key == 'ArrowLeft') dx = -1
	else if (key == 'ArrowRight') dx = 1
	else if (key == 'ArrowUp') dy = -1
	else if (key == 'ArrowDown') dy = 1

	updateElementPosition(dx, dy)
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
			deleteElement(e)
			break
		case 'd':
			if (e.metaKey) duplicateElement(e)
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
	}
}

const handleKeyDown = (e) => {
	if (document.activeElement.tagName == 'INPUT' || focusElementId.value != null) return
	handleGlobalShortcuts(e)

	activeElementId.value != null ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

const slideContainerRef = useTemplateRef('slideContainer')

const slideCursor = ref('none')

const resetCursorVisibility = () => {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 3000)
}

const handleScreenChange = () => {
	inSlideShow.value = document.fullscreenElement

	if (document.fullscreenElement) {
		resetFocus()
		slideContainerRef.value.addEventListener('mousemove', resetCursorVisibility)
	} else {
		slideContainerRef.value.removeEventListener('mousemove', resetCursorVisibility)
	}
}

const isMediaDragOver = ref(false)

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
	files.forEach(async (file) => {
		const fileType = file.type.split('/')[0]
		if (['image', 'video'].includes(fileType)) {
			const fileUploadHandler = new FileUploadHandler()
			const fileDoc = await fileUploadHandler.upload(file, {
				private: false,
			})
			addMediaElement(fileDoc, fileType)
		}
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

onMounted(() => {
	autosaveInterval = setInterval(saveChanges, 60000)
	document.addEventListener('keydown', handleKeyDown)
	document.addEventListener('fullscreenchange', handleScreenChange)
})

onBeforeUnmount(() => {
	clearInterval(autosaveInterval)
	document.removeEventListener('keydown', handleKeyDown)
	document.removeEventListener('fullscreenchange', handleScreenChange)
})
</script>
