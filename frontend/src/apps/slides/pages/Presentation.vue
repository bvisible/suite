<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-50">
		<!-- Navbar -->
		<div class="z-10 flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-200">
			<div class="flex items-center gap-2">
				<Logo />
				<div class="font-semibold">Slides</div>
			</div>

			<input
				ref="newTitleRef"
				v-if="renameMode"
				class="max-w-36 rounded-sm border-none py-1 text-base text-gray-700 focus:ring-gray-500"
				v-model="newTitle"
				@blur="saveTitle"
			/>
			<span v-else class="text-gray-700" @click="enableRenameMode">
				{{ presentation.data?.title }}
			</span>

			<div class="flex gap-2">
				<Button label="Save" size="sm" @click="savePresentation" />
				<Button variant="solid" label="Present" size="sm" />
			</div>
		</div>

		<div
			ref="container"
			class="flex h-full items-center justify-center"
			@click="(e) => clearFocus(e)"
		>
			<SlideNavigationPanel />

			<Slide ref="slide" />

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
	presentation.data.slides[activeSlideIndex.value - 1].elements = JSON.stringify(
		activeSlideElements.value,
	)
	await call('frappe.client.save', {
		doc: presentation.data,
	})
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
	if (!containerRef.value || !slideRef.value.targetRef) return
	addPanAndZoom(containerRef.value, slideRef.value.targetRef)
})

onBeforeUnmount(() => {
	if (!containerRef.value) return
	removePanAndZoom(containerRef.value)
})
</script>
