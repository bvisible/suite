<template>
	<!-- Element Properties Panel -->
	<div
		v-if="activeTab"
		class="fixed z-20 flex h-[94.27%] w-[226px] select-none flex-col border-l bg-white transition-all duration-500 ease-in-out"
		:class="activeTab ? 'right-13' : '-right-[174px]'"
		:style="{ boxShadow: '0 25px 50px -12px rgb(0 0 0 / 0.15)' }"
	>
		<div v-if="activeTab == 'slide'">
			<div class="border-b p-4">
				<div class="flex items-center justify-between">
					<div class="text-2xs font-semibold uppercase text-gray-700">Slide</div>
					<div class="text-2xs font-semibold text-gray-700">
						{{ slideIndex + 1 + ' of ' + presentation.data.slides.length }}
					</div>
				</div>

				<div class="flex items-center justify-between">
					<div class="text-sm text-gray-600">Background</div>
					<ColorPicker v-model="presentation.data.slides[slideIndex].background" />
				</div>
			</div>

			<div class="flex flex-col gap-4 border-b px-4 py-4">
				<div class="text-2xs font-semibold uppercase text-gray-700">Transition</div>
				<FormControl
					type="autocomplete"
					:options="['Slide In', 'Fade', 'None']"
					size="sm"
					variant="subtle"
					:modelValue="slide.transition || 'None'"
					@update:modelValue="(option) => (slide.transition = option.value)"
				/>

				<SliderInput
					label="Duration"
					:rangeStart="0"
					:rangeEnd="4"
					:rangeStep="0.1"
					:modelValue="parseFloat(slide.transitionDuration) || 0"
					@update:modelValue="(value) => (slide.transitionDuration = value)"
				/>
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
						<FlipHorizontal size="20" :strokeWidth="1.2" />
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
						<FlipVertical size="20" :strokeWidth="1.2" />
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
								:strokeWidth="1.2"
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
								:strokeWidth="1.2"
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
						:rangeStart="0.5"
						:rangeEnd="2"
						:rangeStep="0.1"
						:modelValue="parseFloat(activeElement.playbackRate) || 1"
						@update:modelValue="(value) => (activeElement.playbackRate = value)"
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
						:rangeStart="-50"
						:rangeEnd="50"
						:modelValue="parseFloat(activeElement.shadowOffsetX) || 0"
						@update:modelValue="(value) => (activeElement.shadowOffsetX = value)"
					/>

					<SliderInput
						label="Offset Y"
						:rangeStart="-50"
						:rangeEnd="50"
						:modelValue="parseFloat(activeElement.shadowOffsetY) || 0"
						@update:modelValue="(value) => (activeElement.shadowOffsetY = value)"
					/>

					<div class="text-sm text-gray-600">Spread</div>
					<div class="flex items-center justify-between">
						<SliderInput
							class="w-4/5"
							:rangeStart="1"
							:rangeEnd="500"
							:modelValue="parseFloat(activeElement.shadowSpread) || 50"
							@update:modelValue="(value) => (activeElement.shadowSpread = value)"
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
					:rangeStart="0"
					:rangeEnd="100"
					:modelValue="parseFloat(activeElement.opacity) || 100"
					@update:modelValue="(value) => (activeElement.opacity = value)"
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
				<Tooltip text="Slide Properties" :hover-delay="1" placement="left">
					<div
						class="cursor-pointer p-4"
						:class="activeTab == 'slide' ? 'bg-gray-100' : ''"
					>
						<FeatherIcon
							name="layout"
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
		</div>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { Tooltip, FileUploader, FormControl } from 'frappe-ui'
import { FlipHorizontal, FlipVertical, Repeat2, TvMinimalPlay } from 'lucide-vue-next'

import TextPropertyTab from '@/components/TextPropertyTab.vue'
import SliderInput from '@/components/SliderInput.vue'
import NumberInput from '@/components/NumberInput.vue'
import ColorPicker from '@/components/ColorPicker.vue'

import { presentation } from '@/stores/presentation'
import { slideIndex, slideFocus, slide } from '@/stores/slide'
import { activeElement, addTextElement, addMediaElement } from '@/stores/element'

const activeTab = computed(() => {
	if (slideFocus.value) return 'slide'
	if (!activeElement.value) return null
	return activeElement.value.type
})

const hoverOption = ref(null)
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
