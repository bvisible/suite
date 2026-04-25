<template>
	<CollapsibleSection title="Playback">
		<template #default>
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
					<div :class="getPlaybackTextClasses(option.property)">
						{{ option.label }}
					</div>
				</div>
			</div>

			<SliderInput
				label="Speed"
				:rangeStart="0.5"
				:rangeEnd="2"
				:rangeStep="0.1"
				v-model="activeElement.playbackRate"
				@sliderdown="onPlaybackRateUpdateStart"
				@sliderup="onPlaybackRateUpdateEnd"
			/>
		</template>
	</CollapsibleSection>

	<MediaProperties />
</template>

<script setup>
import { ref, inject } from 'vue'

import { Repeat2, TvMinimalPlay } from 'lucide-vue-next'

import MediaProperties from '@/components/MediaProperties.vue'
import SliderInput from '@/components/controls/SliderInput.vue'
import CollapsibleSection from '@/components/controls/CollapsibleSection.vue'

import { currentSlide } from '@/stores/slide'
import { activeElement, activeElementIds } from '@/stores/element'
import { useDeferredCommit } from '@/composables/useDeferredCommit'
import { editElementCommand } from '@/stores/commands'

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
		'text-xs': true,
		'text-gray-800': hoverOption.value == option || activeElement.value[option],
		'text-gray-600': hoverOption.value != option && !activeElement.value[option],
	}
}

const setProperty = inject('setProperty')

const togglePlaybackOption = (option) => {
	setProperty(option, !activeElement.value[option])
}

const setPlaybackRate = (value) => {
	setProperty('playbackRate', parseFloat(value))
}

const { onStart: onPlaybackRateUpdateStart, onEnd: onPlaybackRateUpdateEnd } = useDeferredCommit(
	() => activeElement.value?.playbackRate,
	(oldValue, newValue) =>
		editElementCommand({
			slideId: currentSlide.value?.clientId,
			elementIds: activeElementIds.value,
			property: 'playbackRate',
			oldValue,
			newValue,
		}),
)
</script>
