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
				<Button label="Save" size="sm" @click="savePresentation" />
				<Button variant="solid" label="Present" size="sm" @click="startSlideShow" />
			</div>
		</div>

		<div
			ref="container"
			class="flex h-full items-center justify-center"
			@click="(e) => clearFocus(e)"
		>
			<SlideNavigationPanel />

			<Slide
				ref="slide"
				:style="{
					cursor: inSlideShow ? slideCursor : 'auto',
				}"
			/>

			<SlideElementsPanel />
		</div>
	</div>
</template>

<script setup>
import {
	ref,
	watch,
	onMounted,
	nextTick,
	useTemplateRef,
	onBeforeMount,
	onBeforeUnmount,
} from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Tooltip, call, createResource } from 'frappe-ui'

import { StickyNote } from 'lucide-vue-next'
import Logo from '@/icons/Logo.vue'
import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import Slide from '@/components/Slide.vue'

import { addPanAndZoom, removePanAndZoom } from '@/utils/zoom'
import {
	activeElement,
	activeSlideIndex,
	name,
	presentation,
	activeSlideElements,
	inSlideShow,
} from '@/stores/slide'

const route = useRoute()
const router = useRouter()

const containerRef = useTemplateRef('container')
const slideRef = useTemplateRef('slide')
const newTitleRef = useTemplateRef('newTitleRef')

const showNavigator = ref(false)

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
}

const savePresentation = async () => {
	presentation.data.slides[activeSlideIndex.value - 1].background =
		presentation.data.slides[activeSlideIndex.value - 1].background
	presentation.data.slides[activeSlideIndex.value - 1].elements = JSON.stringify(
		activeSlideElements.value,
		null,
		2,
	)
	await call('frappe.client.save', {
		doc: presentation.data,
	})
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

watch(
	() => route.params.name,
	async () => {
		if (!route.params.name) return
		name.value = route.params.name
		await presentation.fetch()
	},
	{ immediate: true },
)

const slideCursor = ref('auto')

function resetCursorVisibility() {
	let cursorTimer

	slideCursor.value = 'auto'
	clearTimeout(cursorTimer)
	cursorTimer = setTimeout(() => {
		slideCursor.value = 'none'
	}, 2000)
}

const handleScreenChange = () => {
	inSlideShow.value = document.fullscreenElement

	if (document.fullscreenElement) {
		activeElement.value = null
		removePanAndZoom(containerRef.value)
		slideRef.value.targetRef.style.transform = ''
		slideRef.value.targetRef.style.transformOrigin = ''
		slideRef.value.targetRef.style.transform = 'scale(1.5, 1.5)'
		slideRef.value.targetRef.addEventListener('mousemove', resetCursorVisibility)
	} else {
		addPanAndZoom(containerRef.value, slideRef.value.targetRef)
		slideRef.value.targetRef.style.transform = ''
		slideRef.value.targetRef.style.transformOrigin = ''
		slideRef.value.targetRef.removeEventListener('mousemove', resetCursorVisibility)
	}
}

onMounted(() => {
	document.addEventListener('fullscreenchange', handleScreenChange)
	if (!containerRef.value || !slideRef.value.targetRef) return
	addPanAndZoom(containerRef.value, slideRef.value.targetRef)
})

onBeforeUnmount(() => {
	if (!containerRef.value) return
	removePanAndZoom(containerRef.value)
})
</script>
