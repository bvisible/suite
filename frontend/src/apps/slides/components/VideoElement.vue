<template>
	<div @click="handleVideoControls">
		<video
			ref="videoElement"
			:src="element.src"
			:style="videoStyle"
			:autoplay="inSlideShow ? element.autoPlay : false"
			:loop="element.loop"
			:playbackRate="element.playbackRate"
		/>
		<div
			v-if="activeElementIds.includes($attrs['data-index'])"
			class="absolute left-[calc(50%-12px)] top-[calc(50%-12px)] flex h-6 w-6 cursor-pointer items-center justify-center rounded bg-blue-400"
		>
			<component
				size="14"
				:is="isPlaying ? Pause : Play"
				class="text-white stroke-[1.5] ps-[0.5px]"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, useTemplateRef, useAttrs } from 'vue'

import { Play, Pause } from 'lucide-vue-next'

import { inSlideShow } from '@/stores/presentation'
import { activeElementIds, setActiveElements } from '@/stores/element'

const attrs = useAttrs()

const el = useTemplateRef('videoElement')
const isPlaying = ref(false)

const element = defineModel('element', {
	type: Object,
	default: null,
})

const videoStyle = computed(() => ({
	borderRadius: `${element.value.borderRadius}px`,
	borderStyle: element.value.borderStyle || 'none',
	borderColor: element.value.borderColor,
	borderWidth: `${element.value.borderWidth}px`,
	boxShadow: `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`,
}))

const handleVideoControls = (e) => {
	e.stopPropagation()
	if (inSlideShow.value || activeElementIds.value.includes(attrs['data-index'])) {
		const video = el.value
		if (video.paused) {
			isPlaying.value = true
			video.play()
		} else {
			isPlaying.value = false
			video.pause()
		}
	} else setActiveElements([attrs['data-index']])
}
</script>
