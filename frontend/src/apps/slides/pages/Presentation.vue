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
				class="rounded-sm border-none py-1 text-base text-gray-700 focus:ring-gray-500"
				v-model="newTitle"
				@mouseleave="saveTitle"
			/>
			<span v-else class="text-gray-700" @click="enableRenameMode">
				{{ presentation.data?.title }}
			</span>

			<Button variant="solid" label="Present" size="sm" />
		</div>

		<div
			ref="container"
			class="flex h-full items-center justify-center"
			@click="(e) => clearFocus(e)"
		>
			<SlideNavigationPanel
				v-if="presentation.data"
				:slides="presentation.data.slides"
				v-model:activeSlide="activeSlide"
				@addSlide="addSlide"
			/>

			<Slide
				ref="slide"
				:slideElements="slideElements"
				v-model:activeElement="activeElement"
			/>

			<SlideElementsPanel :activeElement="activeElement" />
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick, useTemplateRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Tooltip, call, createResource } from 'frappe-ui'

import { StickyNote } from 'lucide-vue-next'
import Logo from '@/icons/Logo.vue'
import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'
import Slide from '@/components/Slide.vue'

import { addPanAndZoom } from '@/utils/zoom'

const route = useRoute()
const router = useRouter()

const containerRef = useTemplateRef('container')
const slideRef = useTemplateRef('slide')
const newTitleRef = ref(null)

const presentation = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_presentation',
	makeParams: () => ({ name: route.params.name }),
})

const activeSlide = ref(1)
const showNavigator = ref(false)

const addSlide = async () => {
	await call('frappe.client.insert', {
		doc: {
			doctype: 'Slide',
			parenttype: 'Presentation',
			parentfield: 'slides',
			parent: route.params.name,
		},
	})
	await presentation.reload()
	activeSlide.value = presentation.data.slides.length
}

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

const activeElement = ref(null)

const slideElements = ref([])

const renderSlide = () => {
	if (!presentation.data) return

	slideElements.value = []

	let elements = presentation.data.slides[activeSlide.value - 1].elements
	if (!elements) return
	elements = JSON.parse(elements)

	slideElements.value = elements
}

const clearFocus = (e) => {
	if (e.target == containerRef.value) activeElement.value = null
}

watch(
	() => route.params.name,
	async () => {
		if (!route.params.name) return
		await presentation.fetch()
		renderSlide()
	},
	{ immediate: true },
)

watch(
	() => activeSlide.value,
	() => {
		renderSlide()
	},
	{ immediate: true },
)

onMounted(() => {
	if (!containerRef.value || !slideRef.value.targetRef) return
	addPanAndZoom(containerRef.value, slideRef.value.targetRef)
})
</script>

<style scoped>
@tailwind base;
@tailwind components;
@tailwind utilities;

/* width */
::-webkit-scrollbar {
	width: 5px;
}

/* Handle */
::-webkit-scrollbar-thumb {
	background: #dcdcdc;
	border-radius: 4px;
}
</style>
