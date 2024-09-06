<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-50">
		<!-- Navbar -->
		<div class="z-10 flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-200">
			<div class="flex items-center gap-2">
				<Logo />
				<div class="font-semibold">Slides</div>
			</div>

			<span class="text-gray-700">{{ presentation?.title }}</span>

			<Button variant="solid" label="Present" size="sm" />
		</div>

		<div ref="containerRef" class="flex h-full items-center justify-center">
			<!-- Slide Navigation Panel -->
			<SlideNavigator :presentation="presentation" :activeSlide="activeSlide" />

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
import { ref, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'

import { Tooltip, call } from 'frappe-ui'

import { StickyNote } from 'lucide-vue-next'
import Logo from '@/icons/Logo.vue'
import SlideNavigator from '@/components/SlideNavigator.vue'

import { addPanAndZoom } from '@/utils/zoom'

const route = useRoute()

const containerRef = ref(null)
const targetRef = ref(null)
const presentation = ref(null)

const activeSlide = ref(1)
const showNavigator = ref(false)

watch(
	() => route.params.name,
	async () => {
		if (!route.params.name) return
		presentation.value = await call('frappe.client.get', {
			doctype: 'Presentation',
			name: route.params.name,
		})
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
