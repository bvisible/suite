<template>
	<!-- Slide Elements Panel -->
	<div class="fixed right-0 z-20 flex h-[94.2%] w-fit border-l bg-white">
		<div class="flex flex-col justify-between">
			<div>
				<Tooltip text="Text" hover-delay="1" placement="left">
					<div
						class="cursor-pointer p-4"
						:class="activeTab == 'text' ? 'bg-gray-100' : ''"
						@click="addTextElement"
					>
						<FeatherIcon
							name="type"
							class="h-5"
							:class="
								activeTab == 'text' ? 'stroke-[1.8px] text-black' : 'text-[#636363]'
							"
						/>
					</div>
				</Tooltip>
				<Tooltip text="Image" hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="image" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Video" hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="film" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Chart" hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="pie-chart" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Slide Properties" hover-delay="1" placement="left">
					<div
						class="cursor-pointer p-4"
						:class="activeTab == 'slide' ? 'bg-gray-100' : ''"
					>
						<FeatherIcon
							name="sliders"
							class="h-5"
							:class="
								activeTab == 'slide'
									? 'stroke-[1.8px] text-black'
									: 'text-[#636363]'
							"
						/>
					</div>
				</Tooltip>
			</div>
			<Tooltip text="Notes" hover-delay="1" placement="left">
				<div class="cursor-pointer p-4">
					<StickyNote size="20" strokeWidth="1.5" color="#636363" />
				</div>
			</Tooltip>
		</div>
	</div>

	<!-- Element Properties Panel -->
	<div
		class="z-5 fixed flex h-[94.2%] w-[226px] flex-col bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out"
		:class="activeElement ? 'right-13' : '-right-[174px]'"
	>
		<div v-if="activeTab == 'slide'">
			<div class="px-4 pb-4 pt-4 text-2xs uppercase text-gray-600">Slide Properties</div>

			<div class="flex items-center justify-between border-b px-4 pb-3">
				<div class="py-1 text-sm text-gray-800">Background</div>
				<div
					class="h-4 w-4 cursor-pointer rounded-sm border border-gray-700 bg-white shadow-sm"
				></div>
			</div>
		</div>

		<div v-else-if="activeTab == 'text'">
			<TextPropertyTab />
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { Tooltip } from 'frappe-ui'
import { StickyNote } from 'lucide-vue-next'

import { activeElement, activeSlideElements } from '@/stores/slide'
import TextPropertyTab from './TextPropertyTab.vue'

const activeTab = computed(() => {
	if (!activeElement.value) return null
	return activeElement.value.type
})

const addTextElement = () => {
	let element = {
		width: '55px',
		left: '100px',
		top: '100px',
		fontSize: 20,
		fontFamily: 'Arial',
		opacity: 100,
		content: 'Text',
		type: 'text',
	}
	activeSlideElements.value.push(element)
}
</script>
