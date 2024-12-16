<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-100">
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

			<div class="flex select-none gap-2">
				<Button variant="solid" label="Present" size="sm" @click="startSlideShow" />
			</div>
		</div>

		<div
			ref="container"
			class="flex h-full items-center justify-center"
			@click="(e) => clearFocus(e)"
		>
			<SlideNavigationPanel :showNavigator="showNavigator" />

			<Slide ref="slide" :zoom="zoom" />

			<SlideElementsPanel />
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick, useTemplateRef, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { call } from 'frappe-ui'

import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import Slide from '@/components/Slide.vue'

import { usePanAndZoom } from '@/utils/zoom'
import { activeSlideIndex, name, presentation, activeSlideInFocus, position } from '@/stores/slide'
import {
	resetFocus,
	currentFocusedIndex,
	currentDataIndex,
	duplicateElement,
	addTextElement,
} from '@/stores/element'
import { duplicateSlide, changeSlide } from '@/stores/slideActions'
import { saveChanges } from '@/stores/slideActions'

let autosaveInterval = null

const route = useRoute()
const router = useRouter()
const zoom = usePanAndZoom()

const containerRef = useTemplateRef('container')
const slideRef = useTemplateRef('slide')
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
				name: route.params.name,
				new_name: newTitle.value,
			},
		)
		await router.replace({ name: 'Presentation', params: { name: nameSlug } })
	}
	renameMode.value = false
}

const clearFocus = (e) => {
	if (e.target == containerRef.value) {
		resetFocus()
		activeSlideInFocus.value = false
	}
}

const startSlideShow = () => {
	let elem = document.querySelector('.slideContainer')

	if (elem.requestFullscreen) {
		elem.requestFullscreen()
	} else if (elem.webkitRequestFullscreen) {
		elem.webkitRequestFullscreen()
	} else if (elem.msRequestFullscreen) {
		elem.msRequestFullscreen()
	}
}

const updateElementPosition = (dx, dy) => {
	if (!position.value) return
	position.value = { left: position.value.left + dx, top: position.value.top + dy }
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
			changeSlide(activeSlideIndex.value - 1)
			break
		case 'ArrowDown':
			changeSlide(activeSlideIndex.value + 1)
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
	if (document.activeElement.tagName == 'INPUT' || currentFocusedIndex.value != null) return
	handleGlobalShortcuts(e)

	currentDataIndex.value ? handleElementShortcuts(e) : handleSlideShortcuts(e)
}

watch(
	() => route.params.name,
	async () => {
		if (!route.params.name) return
		name.value = route.params.name
		await presentation.fetch()
	},
	{ immediate: true },
)

onMounted(() => {
	zoom.containerElement.value = containerRef.value
	zoom.targetElement.value = slideRef.value.targetRef
	zoom.allowPanAndZoom.value = true
	autosaveInterval = setInterval(saveChanges, 60000)
	document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
	zoom.allowPanAndZoom.value = false
	clearInterval(autosaveInterval)
	document.removeEventListener('keydown', handleKeyDown)
})
</script>
