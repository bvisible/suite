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

		<div ref="containerRef" class="flex h-full items-center justify-center">
			<!-- Slide Navigation Panel -->
			<SlideNavigator
				v-if="presentation.data"
				:slides="presentation.data.slides"
				:activeSlide="activeSlide"
				@addSlide="addSlide"
			/>

			<!-- Slide (Dimensions: 16:9 ratio) -->
			<div ref="targetRef" class="h-[450px] w-[800px] bg-white drop-shadow-lg"></div>

			<!-- Slide Elements Panel -->
			<div class="fixed right-0 z-20 flex h-[743px] w-fit border-l bg-white">
				<div class="flex flex-col justify-between">
					<div>
						<Tooltip text="Text" hover-delay="1" placement="left">
							<div class="cursor-pointer p-3">
								<FeatherIcon name="type" class="h-4.5" color="#636363" />
							</div>
						</Tooltip>
						<Tooltip text="Image" hover-delay="1" placement="left">
							<div class="cursor-pointer p-3">
								<FeatherIcon name="image" class="h-4.5" color="#636363" />
							</div>
						</Tooltip>
						<Tooltip text="Video" hover-delay="1" placement="left">
							<div class="cursor-pointer p-3">
								<FeatherIcon name="film" class="h-4.5" color="#636363" />
							</div>
						</Tooltip>
						<Tooltip text="Chart" hover-delay="1" placement="left">
							<div class="cursor-pointer p-3">
								<FeatherIcon name="pie-chart" class="h-4.5" color="#636363" />
							</div>
						</Tooltip>
					</div>
					<Tooltip text="Notes" hover-delay="1" placement="left">
						<div class="cursor-pointer p-3">
							<StickyNote size="18" strokeWidth="1.5" color="#636363" />
						</div>
					</Tooltip>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { Tooltip, call, createResource } from 'frappe-ui'

import { StickyNote } from 'lucide-vue-next'
import Logo from '@/icons/Logo.vue'
import SlideNavigator from '@/components/SlideNavigator.vue'

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
