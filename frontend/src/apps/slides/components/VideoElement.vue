<template>
	<div @click="handleVideoClick">
		<video
			ref="videoElement"
			:src="element.src"
			:style="videoStyle"
			:autoplay="inSlideShow ? element.autoPlay : false"
			:loop="element.loop"
			:playbackRate="element.playbackRate"
		/>
		<div
			v-if="activeElementIds.includes(element.id)"
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
import { ref, computed, useTemplateRef } from 'vue'

import { Play, Pause } from 'lucide-vue-next'

import { inSlideShow } from '@/stores/presentation'
import { activeElementIds } from '@/stores/element'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const emit = defineEmits(['select'])

const el = useTemplateRef('videoElement')

const isPlaying = ref(false)

const videoStyle = computed(() => ({
	borderRadius: `${element.value.borderRadius}px`,
	borderStyle: element.value.borderStyle || 'none',
	borderColor: element.value.borderColor,
	borderWidth: `${element.value.borderWidth}px`,
	boxShadow: `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`,
}))

const togglePlaying = () => {
	const video = el.value
	if (video.paused) {
		isPlaying.value = true
		video.play()
	} else {
		isPlaying.value = false
		video.pause()
	}
}

const handleVideoClick = (e) => {
	const isActive = activeElementIds.value.includes(element.value.id)

	// in slideshow, always toggle playing on click anywhere
	// in editor, toggle playing only when center play button is clicked

	if (inSlideShow.value || (isActive && e.target !== el.value)) {
		e.stopPropagation()
		togglePlaying()
	}

	// select element if clicked outside play button
	else {
		emit('select', e)
	}
}
</script>
