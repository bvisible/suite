<template>
	<!-- Element Properties Panel -->
	<div
		class="fixed z-20 flex flex-col h-[94.27%] w-[226px] bg-white transition-all duration-500 ease-in-out border-l shadow-[0_10px_24px_-3px_rgba(199,199,199,0.6)]"
		:class="activeTab ? 'right-13' : '-right-[174px]'"
		@wheel.prevent="(e) => e.stopPropagation()"
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
					<ColorPicker v-model="slide.background" />
				</div>
			</div>

			<div class="flex flex-col gap-4 border-b p-4">
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

		<div v-else>
			<TextPropertyTab v-if="activeTab == 'text'" />

			<div v-if="activeTab == 'image'">
				<div class="flex flex-col gap-4 p-4 border-b">
					<div class="text-2xs font-semibold uppercase text-gray-700">Orientation</div>
					<div
						v-for="(direction, index) in imageOrientationProperties"
						:key="index"
						class="flex cursor-pointer items-center justify-between"
						@click="toggleImageOrientation(direction)"
					>
						<div class="text-sm text-gray-600">{{ direction.label }}</div>
						<component :is="direction.icon" size="20" :strokeWidth="1.2" />
					</div>
				</div>
			</div>

			<div v-if="activeTab == 'video'">
				<div class="flex flex-col gap-4 border-b p-4">
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
				<div class="flex flex-col gap-4 border-b p-4">
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

				<div class="flex flex-col gap-4 border-b p-4">
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

			<div
				v-if="activeElement && activeTab != 'video'"
				class="flex flex-col gap-4 p-4 border-b"
			>
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
	<div
		class="fixed right-0 z-20 flex h-[94.27%] border-l bg-white flex-col"
		@wheel.prevent="(e) => e.stopPropagation()"
	>
		<Tooltip text="Text" :hover-delay="1" placement="left">
			<div :class="getTabClasses('text')" @click="addTextElement">
				<FeatherIcon name="type" :class="getIconClasses('text')" />
			</div>
		</Tooltip>
		<Tooltip text="Image" :hover-delay="1" placement="left">
			<FileUploader
				:fileTypes="['image/*']"
				@success="(file) => addMediaElement(file, 'image')"
			>
				<template #default="{ openFileSelector }">
					<div :class="getTabClasses('image')" @click="openFileSelector">
						<FeatherIcon name="image" :class="getIconClasses('image')" />
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
					<div :class="getTabClasses('video')" @click="openFileSelector">
						<FeatherIcon name="film" :class="getIconClasses('video')" />
					</div>
				</template>
			</FileUploader>
		</Tooltip>
		<Tooltip text="Slide Properties" :hover-delay="1" placement="left">
			<div :class="getTabClasses('slide')">
				<FeatherIcon name="layout" :class="getIconClasses('slide')" />
			</div>
		</Tooltip>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { Tooltip, FileUploader, FormControl } from 'frappe-ui'
import { FlipHorizontal, FlipVertical, Repeat2, TvMinimalPlay } from 'lucide-vue-next'

import TextPropertyTab from '@/components/TextPropertyTab.vue'
import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'

import { presentation } from '@/stores/presentation'
import { slideIndex, slideFocus, slide } from '@/stores/slide'
import { activeElement, addTextElement, addMediaElement } from '@/stores/element'

const activeTab = computed(() => {
	if (slideFocus.value) return 'slide'
	if (!activeElement.value) return null
	return activeElement.value.type
})

const getTabClasses = (tab) => {
	const commonClasses = 'cursor-pointer p-4'
	return {
		[commonClasses]: true,
		'bg-gray-100': activeTab.value == tab,
	}
}

const getIconClasses = (tab) => {
	const commonClass = 'h-5'
	return {
		[commonClass]: true,
		'stroke-[1.6px] text-black': activeTab.value == tab,
		'text-gray-600': activeTab.value != tab,
	}
}

const imageOrientationProperties = [
	{
		property: 'invertX',
		label: 'Flip Horizontal',
		icon: FlipHorizontal,
	},
	{
		property: 'invertY',
		label: 'Flip Vertical',
		icon: FlipVertical,
	},
]

const toggleImageOrientation = (direction) => {
	activeElement.value[direction.property] = activeElement.value[direction.property] === 1 ? -1 : 1
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
