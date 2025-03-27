<template>
	<!-- Element Properties Panel -->
	<div
		class="fixed z-20 flex flex-col h-[94.27%] w-[226px] bg-white transition-all duration-300 ease-in-out border-l shadow-[0_10px_24px_-3px_rgba(199,199,199,0.6)]"
		:class="activeTab ? 'right-13' : '-right-[174px]'"
		@wheel.prevent
	>
		<div v-if="activeTab == 'slide'">
			<div :class="sectionClasses">
				<div class="flex items-center justify-between">
					<div :class="sectionTitleClasses">Slide</div>
					<div class="text-2xs font-semibold text-gray-700">
						{{ slideIndex + 1 + ' of ' + presentation.data.slides.length }}
					</div>
				</div>

				<div class="flex items-center justify-between">
					<div class="text-sm text-gray-600">Background</div>
					<ColorPicker v-model="slide.background" />
				</div>
			</div>

			<div :class="sectionClasses">
				<CollapsibleSection :title="'Transition'" :titleClasses="sectionTitleClasses">
					<template #default>
						<div class="flex flex-col gap-4">
							<FormControl
								type="autocomplete"
								:options="['Slide In', 'Fade', 'None']"
								size="sm"
								variant="subtle"
								:modelValue="slide.transition || 'None'"
								@update:modelValue="(option) => setSlideTransition(option)"
							/>

							<SliderInput
								v-show="slide.transition && slide.transition != 'None'"
								label="Duration"
								:rangeStart="0"
								:rangeEnd="4"
								:rangeStep="0.1"
								:modelValue="parseFloat(slide.transitionDuration) || 0"
								@update:modelValue="(value) => (slide.transitionDuration = value)"
							/>
						</div>
					</template>
				</CollapsibleSection>
			</div>
		</div>

		<div v-else>
			<TextPropertyTab v-if="activeTab == 'text'" />

			<div v-if="activeTab == 'image'">
				<div :class="sectionClasses">
					<div :class="sectionTitleClasses">Orientation</div>
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
				<div :class="sectionClasses">
					<div :class="sectionTitleClasses">Playback</div>

					<div class="flex gap-4">
						<div
							v-for="(option, index) in playbackProperties"
							:key="index"
							:class="getPlaybackOptionClasses(option.property)"
							@mouseenter="hoverOption = option.property"
							@mouseleave="hoverOption = null"
							@click="togglePlaybackOption(option.property)"
						>
							<component
								:is="option.icon"
								size="20"
								:strokeWidth="1.2"
								:class="getPlaybackTextClasses(option.property)"
							/>
							<div class="text-xs" :class="getPlaybackTextClasses(option.property)">
								{{ option.label }}
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
				<div :class="sectionClasses">
					<div :class="sectionTitleClasses">Border</div>

					<div
						class="flex h-8 w-full items-center gap-3 justify-between rounded border bg-gray-50 p-[2px] px-2"
					>
						<div
							v-for="(style, index) in ['none', 'solid', 'dashed', 'dotted']"
							:key="index"
							class="flex h-4/5 w-1/4 cursor-pointer items-center justify-center rounded-sm"
							:class="activeElement.borderStyle == style ? 'bg-white shadow' : ''"
							@click="addBorder(style)"
						>
							<Ban v-if="style == 'none'" size="16" class="stroke-[1.5] text-black" />
							<div
								v-else
								class="h-4 w-5 rounded-sm border border-black"
								:style="{ borderStyle: style }"
							></div>
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

				<div :class="sectionClasses">
					<div :class="sectionTitleClasses">Shadow</div>

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

					<div class="flex flex-col gap-1">
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
							<ColorPicker
								class="w-10 justify-end"
								v-model="activeElement.shadowColor"
							/>
						</div>
					</div>
				</div>
			</div>

			<div v-if="activeElement && activeTab != 'video'" :class="sectionClasses">
				<div :class="sectionTitleClasses">Other</div>
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
	<div class="fixed right-0 z-20 flex h-[94.27%] border-l bg-white flex-col" @wheel.prevent>
		<Tooltip text="Text" :hover-delay="1" placement="left">
			<div :class="getTabClasses('text')" @click="addTextElement">
				<Type size="20" :class="getIconClasses('text')" />
			</div>
		</Tooltip>
		<Tooltip text="Image" :hover-delay="1" placement="left">
			<FileUploader
				:fileTypes="['image/*']"
				@success="(file) => handleUploadSuccess(file, 'image')"
				@failure="handleUploadFailure"
			>
				<template #default="{ openFileSelector }">
					<div :class="getTabClasses('image')" @click="openFileSelector">
						<Image size="20" :class="getIconClasses('image')" />
					</div>
				</template>
			</FileUploader>
		</Tooltip>
		<Tooltip text="Video" :hover-delay="1" placement="left">
			<FileUploader
				:fileTypes="['video/*']"
				@success="(file) => handleUploadSuccess(file, 'video')"
				@failure="handleUploadFailure"
			>
				<template #default="{ openFileSelector }">
					<div :class="getTabClasses('video')" @click="openFileSelector">
						<Film size="20" :class="getIconClasses('video')" />
					</div>
				</template>
			</FileUploader>
		</Tooltip>
		<Tooltip text="Slide Properties" :hover-delay="1" placement="left">
			<div :class="getTabClasses('slide')" @click="selectSlide">
				<Layout size="20" :class="getIconClasses('slide')" />
			</div>
		</Tooltip>
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { toast } from 'vue-sonner'

import { Tooltip, FileUploader, FormControl } from 'frappe-ui'
import {
	FlipHorizontal,
	FlipVertical,
	Repeat2,
	TvMinimalPlay,
	Ban,
	Type,
	Image,
	Film,
	Layout,
} from 'lucide-vue-next'

import TextPropertyTab from '@/components/TextPropertyTab.vue'
import SliderInput from '@/components/controls/SliderInput.vue'
import NumberInput from '@/components/controls/NumberInput.vue'
import ColorPicker from '@/components/controls/ColorPicker.vue'

import { presentation } from '@/stores/presentation'
import { slide, slideIndex, selectSlide } from '@/stores/slide'
import {
	activeElements,
	activeElement,
	focusElementId,
	addTextElement,
	addMediaElement,
} from '@/stores/element'
import CollapsibleSection from './controls/CollapsibleSection.vue'

const activeTab = computed(() => {
	if (activeElement.value) return activeElement.value.type
	return 'slide'
})

const getTabClasses = (tab) => {
	const commonClasses = 'cursor-pointer p-4'
	return {
		[commonClasses]: true,
		'bg-gray-100': activeTab.value == tab,
	}
}

const getIconClasses = (tab) => {
	const commonClass = 'stroke-[1.5]'
	return {
		[commonClass]: true,
		'stroke-[1.6] text-black': activeTab.value == tab,
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

const sectionClasses = 'flex flex-col gap-4 p-4 border-b'
const sectionTitleClasses = 'text-2xs font-semibold uppercase text-gray-700'

const hoverOption = ref(null)

const playbackProperties = [
	{
		property: 'autoplay',
		label: 'Autoplay',
		icon: TvMinimalPlay,
	},
	{
		property: 'loop',
		label: 'Loop',
		icon: Repeat2,
	},
]

const getPlaybackOptionClasses = (option) => {
	return {
		'cursor-pointer flex flex-col w-1/2 items-center justify-center gap-1 rounded border p-1': true,
		'border-gray-800 bg-gray-50': hoverOption.value == option || activeElement.value[option],
	}
}

const getPlaybackTextClasses = (option) => {
	return {
		'text-gray-800': hoverOption.value == option || activeElement.value[option],
		'text-gray-600': hoverOption.value != option && !activeElement.value[option],
	}
}

const togglePlaybackOption = (option) => {
	activeElement.value[option] = !activeElement.value[option]
}

const handleUploadSuccess = (file, type) => {
	addMediaElement(file, type)
	toast.success('Uploaded: ' + file.file_name)
}

const handleUploadFailure = () => {
	toast.error('Upload failed. Please try again.')
}

const addBorder = (style) => {
	activeElement.value.borderStyle = style
	activeElement.value.borderWidth = 1
}

const setSlideTransition = (option) => {
	slide.value.transition = option.value
	if (option.value == 'None') slide.value.transitionDuration = 0
	else slide.value.transitionDuration = 1
}
</script>

<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
