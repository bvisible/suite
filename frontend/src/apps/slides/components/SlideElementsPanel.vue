<template>
	<!-- Element Properties Panel -->
	<div
		v-if="activeElement"
		class="fixed z-20 flex h-[94.27%] w-[226px] select-none flex-col border-l bg-white transition-all duration-500 ease-in-out"
		:class="activeElement ? 'right-13' : '-right-[174px]'"
		:style="{ boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.15)' }"
	>
		<div v-if="activeTab == 'slide'">
			<div class="border-b p-4">
				<div class="flex items-center justify-between">
					<div class="text-2xs font-semibold uppercase text-gray-700">Slide</div>
					<div class="text-2xs font-semibold text-gray-700">
						{{ activeSlideIndex + 1 + ' of ' + presentation.data.slides.length }}
					</div>
				</div>

				<div class="flex items-center justify-between">
					<div class="text-sm text-gray-600">Background</div>
					<ColorPicker v-model="presentation.data.slides[activeSlideIndex].background" />
				</div>
			</div>
		</div>

		<div v-else class="flex flex-col">
			<div v-if="activeTab == 'text'">
				<TextPropertyTab />
			</div>

			<div v-if="activeTab == 'image'">
				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="text-2xs font-semibold uppercase text-gray-700">Orientation</div>
					<div
						class="flex cursor-pointer items-center justify-between pb-2 pe-2"
						@click="
							activeElement.invertX == 1
								? (activeElement.invertX = -1)
								: (activeElement.invertX = 1)
						"
					>
						<div class="text-sm text-gray-600">Flip Horizontally</div>
						<FlipHorizontal size="20" strokeWidth="1.2" />
					</div>
					<div
						class="flex cursor-pointer items-center justify-between pb-2 pe-2"
						@click="
							activeElement.invertY == 1
								? (activeElement.invertY = -1)
								: (activeElement.invertY = 1)
						"
					>
						<div class="text-sm text-gray-600">Flip Vertically</div>
						<FlipVertical size="20" strokeWidth="1.2" />
					</div>
				</div>
			</div>

			<div v-if="activeTab == 'video'">
				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="text-2xs font-semibold uppercase text-gray-700">Playback</div>

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
					<div class="text-2xs font-semibold uppercase text-gray-700">Border</div>

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

					<div v-if="activeElement.borderStyle != 'none'" class="flex flex-col gap-4">
						<div class="flex items-center justify-between">
							<div class="text-sm text-gray-600">Width</div>
							<div class="h-[30px] w-28">
								<NumberInput
									v-model="activeElement.borderWidth"
									suffix="px"
									:rangeStart="0"
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

						<div class="flex items-center justify-between">
							<div class="text-sm text-gray-600">Colour</div>
							<ColorPicker v-model="activeElement.borderColor" />
						</div>
					</div>
				</div>

				<div class="flex flex-col gap-4 border-b px-4 py-4">
					<div class="text-2xs font-semibold uppercase text-gray-700">Shadow</div>

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
					<div class="flex items-center justify-between">
						<SliderInput
							class="w-4/5"
							v-model="activeElement.shadowSpread"
							:rangeStart="1"
							:rangeEnd="500"
							:default="50"
							:showInput="false"
						/>
						<ColorPicker v-model="activeElement.shadowColor" />
					</div>
				</div>
			</div>

			<div v-if="activeElement && activeTab != 'video'" class="flex flex-col gap-4 px-4 py-4">
				<div class="text-2xs font-semibold uppercase text-gray-700">Other</div>
				<SliderInput
					label="Opacity"
					v-model="activeElement.opacity"
					:rangeStart="0"
					:rangeEnd="100"
				/>
			</div>
		</div>
	</div>

	<!-- Slide Elements Panel -->
	<div class="fixed right-0 z-20 flex h-[94.27%] w-fit select-none border-l bg-white">
		<div class="flex flex-col justify-between">
			<div>
				<Tooltip text="Text" :hover-delay="1" placement="left">
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
				<Tooltip text="Image" :hover-delay="1" placement="left">
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
				<Tooltip text="Video" :hover-delay="1" placement="left">
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
				<Tooltip text="Chart" :hover-delay="1" placement="left">
					<div class="cursor-pointer p-4">
						<FeatherIcon name="pie-chart" class="h-5" color="#636363" />
					</div>
				</Tooltip>
				<Tooltip text="Slide Properties" :hover-delay="1" placement="left">
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
			<Tooltip text="Notes" :hover-delay="1" placement="left">
				<div class="cursor-pointer p-4">
					<StickyNote size="20" strokeWidth="1.5" color="#636363" />
				</div>
			</Tooltip>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'

import { Tooltip, FileUploader } from 'frappe-ui'

import { FlipHorizontal, FlipVertical, Repeat2, StickyNote, TvMinimalPlay } from 'lucide-vue-next'

import {
	activeElement,
	activeSlideIndex,
	activeSlideElements,
	presentation,
	currentDataIndex,
	setActiveElement,
} from '@/stores/slide'
import SliderInput from './SliderInput.vue'
import TextPropertyTab from './TextPropertyTab.vue'
import NumberInput from './NumberInput.vue'
import ColorPicker from './ColorPicker.vue'

const activeTab = computed(() => {
	if (!activeElement.value) return null
	return activeElement.value.type
})

const guessTextColor = () => {
	const rgbString = document.querySelector('.slide')?.style.backgroundColor
	const match = rgbString?.match(/^rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)(?:,\s*(\d*\.?\d+)\s*)?\)$/)
	if (!match) return 'hsl(0, 0%, 0%)'
	const r = parseInt(match[1], 10)
	const g = parseInt(match[2], 10)
	const b = parseInt(match[3], 10)
	const luminance = 0.2989 * r + 0.587 * g + 0.114 * b
	return luminance > 128 ? 'hsl(0, 0%, 0%)' : 'hsl(0, 0%, 100%)'
}

const addTextElement = () => {
	const lastTextElement = activeSlideElements.value
		.reverse()
		.find((element) => element.type == 'text')

	const element = {
		left: 100,
		top: 100,
		opacity: 100,
		content: 'Text',
		type: 'text',
	}

	if (lastTextElement) {
		element.width = lastTextElement.width
		element.fontSize = lastTextElement.fontSize
		element.fontFamily = lastTextElement.fontFamily
		element.fontWeight = lastTextElement.fontWeight
		element.color = lastTextElement.color
		element.lineHeight = lastTextElement.lineHeight
		element.letterSpacing = lastTextElement.letterSpacing
	} else {
		element.width = 65
		element.fontSize = 30
		element.fontFamily = 'Inter'
		element.fontWeight = 'normal'
		element.color = guessTextColor()
		element.lineHeight = 1
		element.letterSpacing = 0
	}
	activeSlideElements.value.push(element)
	nextTick(() => setActiveElement(element))
}

const addMediaElement = (file, type) => {
	let element = {
		width: 300,
		left: 200,
		top: 75,
		opacity: 100,
		type: type,
		src: file.file_url,
		borderStyle: 'none',
		borderWidth: 0,
		borderRadius: 0,
		borderColor: '#000000',
		shadowOffsetX: 0,
		shadowOffsetY: 0,
		shadowSpread: 0,
		shadowColor: '#000000',
	}
	if (type == 'video') {
		element.autoPlay = false
		element.loop = false
		element.playbackRate = 1
	}
	activeSlideElements.value.push(element)
	nextTick(() => setActiveElement(element))
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
