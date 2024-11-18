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
			v-if="currentDataIndex == $attrs['data-index']"
			class="absolute left-[calc(50%-12px)] top-[calc(50%-12px)] flex h-6 w-6 cursor-pointer items-center justify-center rounded bg-blue-400"
		>
			<FeatherIcon
				:name="isPlaying ? 'pause' : 'play'"
				class="stroke-width-3 h-3 ps-[0.5px] text-white"
			></FeatherIcon>
		</div>
	</div>
</template>

<script setup>
import { ref, useTemplateRef, computed, inject, useAttrs } from 'vue'
import { activeElement, currentDataIndex, inSlideShow } from '@/stores/slide'

const attrs = useAttrs()
const setActiveElement = inject('setActiveElement')

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
	if (inSlideShow.value || currentDataIndex.value != attrs['data-index']) {
		const video = el.value
		if (video.paused) {
			isPlaying.value = true
			video.play()
		} else {
			isPlaying.value = false
			video.pause()
		}
	} else setActiveElement(e, element.value)
}
</script>
