<template>
	<!-- Render Video Element -->
	<div
		class="fixed"
		:style="{
			width: elementStyle.width,
			left: elementStyle.left,
			height: unref(rect.height) + 'px',
			top: elementStyle.top,
		}"
	>
		<video
			ref="videoElement"
			class="videoElement"
			:style="elementStyle"
			:src="element.src"
			:autoplay="element.autoPlay"
			:loop="element.loop"
			:playbackRate="element.playbackRate"
		/>
		<div
			v-if="isEqual(activeElement, element) || inSlideShow"
			class="absolute left-[calc(50%-12px)] top-[calc(50%-12px)] flex h-6 w-6 cursor-pointer items-center justify-center rounded bg-blue-400"
			@click="handleVideoControls"
		>
			<FeatherIcon
				:name="isPlaying ? 'pause' : 'play'"
				class="stroke-width-3 h-3 ps-[0.5px] text-white"
			></FeatherIcon>
		</div>
		<Resizer
			v-if="isEqual(activeElement, element)"
			:element="element"
			:isResizing="isResizing"
		/>
	</div>
</template>

<script setup>
import { ref, unref, useTemplateRef, computed } from 'vue'
import Resizer from './Resizer.vue'
import { useElementBounding } from '@vueuse/core'
import { activeElement, inSlideShow } from '@/stores/slide'
import { isEqual } from 'lodash'
import { Feather } from 'lucide-vue-next'

const isResizing = ref(false)

const el = useTemplateRef('videoElement')
const isPlaying = ref(false)

const rect = useElementBounding(el)

const element = defineModel('element', {
	type: Object,
	default: null,
})

const elementStyle = computed(() => ({
	padding: '2px',
	position: 'fixed',
	width: element.value.width,
	height: 'auto',
	left: element.value.left,
	top: element.value.top,
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
