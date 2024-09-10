<template>
	<!-- Slide Elements Panel -->
	<div class="fixed right-0 z-20 flex h-[743px] w-fit border-l bg-white">
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
		class="z-5 fixed flex h-[743px] w-[226px] flex-col bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out"
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
			<div class="flex flex-col gap-4 px-4 py-2">
				<div class="flex items-center justify-between">
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="bold" class="h-4" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="italic" class="h-4" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="underline" class="h-4" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<Strikethrough size="16" strokeWidth="1.5" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<CaseUpper size="20" strokeWidth="1.5" />
					</div>
				</div>

				<div class="flex items-center justify-between">
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-left" class="h-4.5" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-center" class="h-4.5" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-right" class="h-4.5" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="align-justify" class="h-4.5" />
					</div>
					<div class="cursor-pointer rounded-sm p-1">
						<FeatherIcon name="list" class="h-4.5" />
					</div>
				</div>
			</div>

			<div class="flex flex-col gap-4 border-y px-4 py-4">
				<div class="text-2xs uppercase text-gray-600">Font</div>
				<FormControl type="autocomplete" :options="textFonts" size="sm" variant="subtle" />

				<div class="flex items-center justify-between">
					<div class="flex h-7 w-3/5 rounded border bg-gray-100">
						<div class="flex w-10 cursor-pointer items-center justify-center">
							<FeatherIcon name="minus" class="h-3" strokeWidth="2" />
						</div>
						<div class="bg-white">
							<input
								type="number"
								class="h-full w-12 border-none p-0 text-center text-xs font-semibold text-gray-800 focus:outline-none focus:ring-0"
							/>
						</div>
						<div class="flex w-10 cursor-pointer items-center justify-center rounded-r">
							<FeatherIcon name="plus" class="h-3" strokeWidth="2" />
						</div>
					</div>
					<div class="h-6 w-6 cursor-pointer rounded border bg-black shadow-sm"></div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { Tooltip, FormControl } from 'frappe-ui'
import { StickyNote, Strikethrough, CaseUpper } from 'lucide-vue-next'

const props = defineProps({
	activeElement: HTMLElement,
})

const activeTab = computed(() => {
	if (props.activeElement?.classList.contains('textElement')) return 'text'
	else if (props.activeElement?.classList.contains('slide')) return 'slide'
	return null
})

const addTextElement = () => {
	const text = document.createElement('div')
	text.innerText = 'Text'
	text.style.fontFamily = 'Arial'
	text.style.fontSize = '16px'
	text.style.margin = '14px'
	text.style.color = '#000'
	text.style.zIndex = '100'
	text.style.top = '200px'
	text.style.left = '350px'
	text.style.position = 'absolute'
	text.style.width = 'fit-content'
	text.classList.add('textElement')

	document.querySelector('.slide').appendChild(text)
}

const textFonts = [
	{
		label: 'Arial',
		value: 'Arial',
	},
	{
		label: 'Roboto',
		value: 'Roboto',
	},
	{
		label: 'Helvetica',
		value: 'Helvetica',
	},
]
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
