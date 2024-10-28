<template>
	<video
		ref="videoElement"
		:src="element.src"
		:style="videoStyle"
		:autoplay="element.autoPlay"
		:loop="element.loop"
		:playbackRate="element.playbackRate"
	/>
	<div
		v-if="isEqual(activeElement, element)"
		class="absolute left-[calc(50%-12px)] top-[calc(50%-12px)] flex h-6 w-6 cursor-pointer items-center justify-center rounded bg-blue-400"
		@click="handleVideoControls"
	>
		<FeatherIcon
			:name="isPlaying ? 'pause' : 'play'"
			class="stroke-width-3 h-3 ps-[0.5px] text-white"
		></FeatherIcon>
	</div>
</template>

<script setup>
import { ref, useTemplateRef, computed } from 'vue'
import { activeElement } from '@/stores/slide'
import { isEqual } from 'lodash'

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
	const video = el.value
	if (video.paused) {
		isPlaying.value = true
		video.play()
	} else {
		isPlaying.value = false
		video.pause()
	}
}
</script>
