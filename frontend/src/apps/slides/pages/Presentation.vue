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
			<div
				class="fixed z-20 h-[743px] w-44 overflow-y-auto border-r bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out"
				:class="showNavigator ? 'left-0' : '-left-44'"
			>
				<div class="flex flex-col gap-4 p-4">
					<div
						v-for="i in presentation?.slides.length"
						:key="i"
						class="h-20 cursor-pointer rounded border shadow-lg shadow-gray-100"
						:class="activeSlide == i ? 'border-gray-500' : 'border-gray-300'"
						@click="activeSlide = i"
					>
						<div class="p-1 text-xs text-gray-500">{{ i }}</div>
					</div>

					<div
						class="flex h-20 cursor-pointer items-center justify-center rounded border border-dashed border-gray-300 shadow-lg shadow-gray-100"
					>
						<FeatherIcon name="plus" class="h-3.5 text-gray-500" />
					</div>
				</div>
			</div>

			<!-- Slide Navigator Toggle -->
			<div
				class="fixed z-10 flex h-8 w-8 cursor-pointer items-center justify-center transition-all duration-500 ease-in-out"
				:class="
					showNavigator
						? 'bottom-2 left-44'
						: 'bottom-2 left-2 rounded bg-white shadow-md shadow-gray-400'
				"
				@click="showNavigator = !showNavigator"
			>
				<PanelLeftClose v-if="showNavigator" size="16" strokeWidth="1.5" />
				<PanelLeftOpen v-else size="16" strokeWidth="1.5" />
			</div>

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

import { PanelLeftOpen, PanelLeftClose, StickyNote } from 'lucide-vue-next'
import Logo from '@/icons/Logo.vue'

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
