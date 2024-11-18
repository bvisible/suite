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
			<SlideNavigationPanel />

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
import {
	activeElement,
	focusedElement,
	activeSlideIndex,
	name,
	presentation,
	activeSlideElements,
} from '@/stores/slide'

let autosaveInterval = null

const route = useRoute()
const router = useRouter()
const zoom = usePanAndZoom()

const containerRef = useTemplateRef('container')
const slideRef = useTemplateRef('slide')
const newTitleRef = useTemplateRef('newTitleRef')

const renameMode = ref(false)
const newTitle = ref('')

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
	if (e.target == containerRef.value) activeElement.value = null
	focusedElement.value = null
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

const saveChanges = async () => {
	if (!presentation.data) return
	presentation.data.slides[activeSlideIndex.value].elements = JSON.stringify(
		activeSlideElements.value,
		null,
		2,
	)
	await call('frappe.client.save', {
		doc: presentation.data,
	})
	await presentation.reload()
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
})

onBeforeUnmount(() => {
	zoom.allowPanAndZoom.value = false
	clearInterval(autosaveInterval)
})
</script>
