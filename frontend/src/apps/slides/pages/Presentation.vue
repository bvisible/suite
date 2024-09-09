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
			ref="containerRef"
			class="flex h-full items-center justify-center"
			@click="(e) => e.target == containerRef && clearFocus(e)"
		>
			<SlideNavigationPanel
				v-if="presentation.data"
				:slides="presentation.data.slides"
				:activeSlide="activeSlide"
				@addSlide="addSlide"
			/>

			<!-- Slide (Dimensions: 16:9 ratio) -->
			<div
				ref="targetRef"
				class="slide h-[450px] w-[800px] bg-white drop-shadow-lg"
				@click="(e) => focusOnElement(e)"
			></div>

			<SlideElementsPanel :activeElement="activeElement" />
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Tooltip, call, createResource } from 'frappe-ui'

import { StickyNote } from 'lucide-vue-next'
import Logo from '@/icons/Logo.vue'
import SlideNavigationPanel from '@/components/SlideNavigationPanel.vue'
import SlideElementsPanel from '@/components/SlideElementsPanel.vue'

import { addPanAndZoom } from '@/utils/zoom'

const route = useRoute()
const router = useRouter()

const containerRef = ref(null)
const targetRef = ref(null)
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

const focusOnElement = (e) => {
	e.stopPropagation()

	if (activeElement.value == e.target) return

	clearFocus({ target: activeElement.value })

	if (e.target == targetRef.value || e.target.classList.contains('textElement')) {
		activeElement.value = e.target
		activeElement.value.classList.add('ring-[1.5px]', 'ring-[#808080]/50', 'cursor-pointer')
	}
}

const clearFocus = (e) => {
	if (activeElement.value) {
		activeElement.value.classList.remove('ring-[1.5px]', 'ring-[#808080]/50', 'cursor-pointer')
		activeElement.value = null
	}
}

watch(
	() => route.params.name,
	async () => {
		if (!route.params.name) return
		presentation.fetch()
	},
	{ immediate: true },
)

onMounted(() => {
	if (!containerRef.value || !targetRef.value) return
	addPanAndZoom(containerRef.value, targetRef.value)
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
