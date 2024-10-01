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
								activeTab == 'text' ? 'stroke-[1.6px] text-black' : 'text-[#636363]'
							"
						/>
					</div>
				</Tooltip>
				<Tooltip text="Image" hover-delay="1" placement="left">
					<FileUploader
						:fileTypes="['image/*']"
						@success="(file) => addMediaElement(file, 'image')"
					>
						<template #default="{ openFileSelector }">
							<div
								class="cursor-pointer p-4"
								:class="activeTab == 'image' ? 'bg-gray-100' : ''"
								@click="openFileSelector"
							>
								<FeatherIcon
									name="image"
									class="h-5"
									:class="
										activeTab == 'image'
											? 'stroke-[1.6px] text-black'
											: 'text-[#636363]'
									"
								/>
							</div>
						</template>
					</FileUploader>
				</Tooltip>
				<Tooltip text="Video" hover-delay="1" placement="left">
					<FileUploader
						:fileTypes="['video/*']"
						@success="(file) => addMediaElement(file, 'video')"
					>
						<template #default="{ openFileSelector }">
							<div
								class="cursor-pointer p-4"
								:class="activeTab == 'video' ? 'bg-gray-100' : ''"
								@click="openFileSelector"
							>
								<FeatherIcon
									name="film"
									class="h-5"
									:class="
										activeTab == 'video'
											? 'stroke-[1.6px] text-black'
											: 'text-[#636363]'
									"
								/>
							</div>
						</template>
					</FileUploader>
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
									? 'stroke-[1.6px] text-black'
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
		v-if="activeElement"
		class="z-5 fixed flex h-[94.2%] w-[226px] flex-col bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out"
		:class="activeElement ? 'right-13' : '-right-[174px]'"
	>
		<div v-if="activeTab == 'slide'">
			<div class="px-4 pb-4 pt-4 text-2xs uppercase text-gray-600">Slide Properties</div>

			<div class="p-4 text-sm text-gray-800">Background</div>
		</div>

		<div v-else class="flex flex-col">
			<div v-if="activeTab == 'text'">
				<TextPropertyTab />
			</div>

			<div v-if="activeTab == 'image'">
				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="mb-1 text-2xs uppercase text-gray-900">Orientation</div>
					<div
						class="flex cursor-pointer items-center justify-between pb-2 pe-2"
						@click="activeElement.invertX = !activeElement.invertX"
					>
						<div class="text-sm text-gray-600">Invert Horizontally</div>
						<FlipHorizontal size="20" strokeWidth="1.2" />
					</div>
					<div
						class="flex cursor-pointer items-center justify-between pb-2 pe-2"
						@click="activeElement.invertY = !activeElement.invertY"
					>
						<div class="text-sm text-gray-600">Invert Vertically</div>
						<FlipVertical size="20" strokeWidth="1.2" />
					</div>
				</div>
			</div>

			<div v-if="activeTab == 'video'">
				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="mb-1 text-2xs uppercase text-gray-900">Playback</div>

					<div class="flex gap-4">
						<div
							class="flex w-1/2 cursor-pointer flex-col items-center justify-center gap-1 rounded border p-1"
							:class="
								hoverOption == 'autoplay' || activeElement.autoPlay
									? 'border-gray-800 bg-gray-50'
									: ''
							"
							@mouseenter="hoverOption = 'autoplay'"
							@mouseleave="hoverOption = null"
							@click="activeElement.autoPlay = !activeElement.autoPlay"
						>
							<TvMinimalPlay
								size="20"
								strokeWidth="1.2"
								:class="
									hoverOption == 'autoplay' || activeElement.autoPlay
										? 'text-gray-800'
										: 'text-gray-600'
								"
							/>
							<div
								class="text-xs"
								:class="
									hoverOption == 'autoplay' || activeElement.autoPlay
										? 'text-gray-800'
										: 'text-gray-600'
								"
							>
								Autoplay
							</div>
						</div>
						<div
							class="flex w-1/2 cursor-pointer flex-col items-center justify-center gap-1 rounded border p-1"
							:class="
								hoverOption == 'loop' || activeElement.loop
									? 'border-gray-800 bg-gray-50'
									: ''
							"
							@mouseenter="hoverOption = 'loop'"
							@mouseleave="hoverOption = null"
							@click="activeElement.loop = !activeElement.loop"
						>
							<Repeat2
								size="20"
								strokeWidth="1.2"
								:class="
									hoverOption == 'loop' || activeElement.loop
										? 'text-gray-800'
										: 'text-gray-600'
								"
							/>
							<div
								class="text-xs"
								:class="
									hoverOption == 'loop' || activeElement.loop
										? 'text-gray-800'
										: 'text-gray-600'
								"
							>
								Loop
							</div>
						</div>
					</div>

					<SliderInput
						label="Speed"
						v-model="activeElement.playbackRate"
						:rangeStart="0.5"
						:rangeEnd="2"
						:rangeStep="0.1"
						:default="1"
					/>
				</div>
			</div>

			<div v-if="['image', 'video'].includes(activeTab)">
				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="mb-1 text-2xs uppercase text-gray-900">Border</div>

					<div
						class="flex h-[34px] w-full items-center justify-between gap-3 rounded border bg-gray-50 p-[1px] px-[5px]"
					>
						<div
							class="flex h-4/5 w-1/4 cursor-pointer items-center justify-center rounded-sm"
							:class="activeElement.borderStyle == 'none' ? 'bg-white shadow' : ''"
							@click="activeElement.borderStyle = 'none'"
						>
							<FeatherIcon name="slash" class="h-4 text-black" />
						</div>
						<div
							class="flex h-4/5 w-1/4 cursor-pointer items-center justify-center rounded-sm"
							:class="activeElement.borderStyle == 'solid' ? 'bg-white shadow' : ''"
							@click="activeElement.borderStyle = 'solid'"
						>
							<div class="h-4 w-5 rounded-sm border border-solid border-black"></div>
						</div>
						<div
							class="flex h-4/5 w-1/4 cursor-pointer items-center justify-center rounded-sm"
							:class="activeElement.borderStyle == 'dashed' ? 'bg-white shadow' : ''"
							@click="activeElement.borderStyle = 'dashed'"
						>
							<div class="h-4 w-5 rounded-sm border border-dashed border-black"></div>
						</div>
						<div
							class="flex h-4/5 w-1/4 cursor-pointer items-center justify-center rounded-sm"
							:class="activeElement.borderStyle == 'dotted' ? 'bg-white shadow' : ''"
							@click="activeElement.borderStyle = 'dotted'"
						>
							<div class="h-4 w-5 rounded-sm border border-dotted border-black"></div>
						</div>
					</div>

					<div class="flex items-center justify-between">
						<div class="text-sm text-gray-600">Width</div>
						<div class="h-[30px] w-28">
							<NumberInput
								v-model="activeElement.borderWidth"
								suffix="px"
								:rangeStart="1"
								:rangeEnd="50"
							/>
						</div>
					</div>

					<div class="flex items-center justify-between">
						<div class="text-sm text-gray-600">Radius</div>
						<div class="h-[30px] w-28">
							<NumberInput
								v-model="activeElement.borderRadius"
								suffix="px"
								:rangeStart="1"
								:rangeEnd="50"
							/>
						</div>
					</div>

					<div class="text-sm text-gray-600">Colour</div>
				</div>

				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="mb-1 text-2xs uppercase text-gray-900">Shadow</div>

					<SliderInput
						label="Offset X"
						v-model="activeElement.shadowOffsetX"
						:rangeStart="-50"
						:rangeEnd="50"
						:default="0"
					/>

					<SliderInput
						label="Offset Y"
						v-model="activeElement.shadowOffsetY"
						:rangeStart="-50"
						:rangeEnd="50"
						:default="0"
					/>

					<div class="text-sm text-gray-600">Spread</div>
					<SliderInput
						class="w-4/5"
						v-model="activeElement.shadowSpread"
						:rangeStart="1"
						:rangeEnd="500"
						:default="50"
						:showInput="false"
					/>
				</div>
			</div>

			<div class="flex flex-col gap-4 border-b px-4 py-4">
				<SliderInput
					label="Transparency"
					v-model="activeElement.opacity"
					:rangeStart="0"
					:rangeEnd="100"
				/>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { Tooltip, FileUploader, FormControl, Switch } from 'frappe-ui'
import {
	FlipHorizontal,
	FlipVertical,
	Repeat2,
	StickyNote,
	TvMinimalPlay,
	Undo,
} from 'lucide-vue-next'

import { activeElement, activeSlideIndex, activeSlideElements, presentation } from '@/stores/slide'
import SliderInput from './SliderInput.vue'
import TextPropertyTab from './TextPropertyTab.vue'
import NumberInput from './NumberInput.vue'

const activeTab = computed(() => {
	if (!activeElement.value) return null
	return activeElement.value.type
})

const addTextElement = () => {
	let element = {
		width: '55px',
		left: '50%',
		top: '50%',
		fontSize: 20,
		fontFamily: 'Arial',
		opacity: 100,
		content: 'Text',
		type: 'text',
		color:
			presentation.data.slides[activeSlideIndex.value].background_color == '#ffffff'
				? '#000000'
				: '#ffffff',
		lineHeight: 1,
		letterSpacing: 0,
	}
	activeSlideElements.value.push(element)
}

const addMediaElement = (file, type) => {
	let element = {
		width: '300px',
		left: 'calc(50% - 150px)',
		top: 'calc(50% - 150px)',
		opacity: 100,
		type: type,
		src: file.file_url,
	}
	activeSlideElements.value.push(element)
}

const hoverOption = ref(null)
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
