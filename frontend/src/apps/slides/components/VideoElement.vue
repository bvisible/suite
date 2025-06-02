<template>
	<div
		@click="handleVideoClick"
		@mouseenter="hoveringOverVideo = true"
		@mouseleave="hoveringOverVideo = false"
	>
		<video
			ref="videoElement"
			:style="videoStyle"
			:autoplay="inSlideShow ? element.autoplay : false"
			:loop="element.loop"
			:playbackRate="element.playbackRate"
			@timeupdate="updateProgress"
			@loadedmetadata="updateDuration"
			@ended="resetProgress"
			preload="auto"
		>
			<source :src="`/api/method/slides.api.get_video?src=${element.src}`" />
		</video>
		<div
			class="transition-opacity duration-500 ease-in-out absolute top-0 left-0 w-full h-full"
			:class="{ 'opacity-0': !showProgressBar }"
			:style="gradientOverlayStyles"
		>
			<div
				v-if="activeElementIds.includes(element.id)"
				class="absolute inset-[calc(50%-16px)] flex h-8 w-8 cursor-pointer items-center justify-center rounded-lg bg-white-overlay-100 opacity-80"
			>
				<component
					size="16"
					:is="isPlaying ? Pause : Play"
					class="text-white stroke-[1.5] ps-[0.5px]"
				/>
			</div>
			<div
				v-if="showProgressBar"
				class="absolute h-[6px] hover:h-2 w-full bottom-0 left-0 cursor-pointer transition-all duration-100 ease-linear"
				@click.stop="seekTimestamp"
			>
				<div
					ref="progressBar"
					class="bg-white-overlay-900 opacity-30 w-full h-full absolute left-0 top-0"
				></div>
				<div
					class="bg-white-overlay-900 opacity-40 h-full absolute left-0 top-0 transition-width duration-300 ease-linear"
					:style="{ width: `${progress}%` }"
				></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, useTemplateRef, inject } from 'vue'

import { Play, Pause } from 'lucide-vue-next'

import { inSlideShow } from '@/stores/presentation'
import { activeElementIds } from '@/stores/element'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const el = useTemplateRef('videoElement')

const isPlaying = ref(false)

const videoStyle = computed(() => ({
	width: '100%',
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
}

const duration = ref(0)
const progress = ref(0)

const updateProgress = () => {
	const video = el.value
	if (duration.value) {
		progress.value = Math.round((video.currentTime / duration.value) * 100)
	}
}

const updateDuration = () => {
	const video = el.value
	if (video.duration) {
		duration.value = video.duration
	}
}

const hoveringOverVideo = ref(false)

const showProgressBar = computed(() => {
	// In editor, show it when video is active
	const isActive = activeElementIds.value.includes(element.value.id)

	// During slideshow, show it only if user is hovering over video
	const slideshowHovering = inSlideShow.value && hoveringOverVideo.value

	return isActive || slideshowHovering
})

const progressBarRef = useTemplateRef('progressBar')

const seekTimestamp = (e) => {
	const progressBarRect = progressBarRef.value.getBoundingClientRect()
	const percentage = (e.clientX - progressBarRect.left) / progressBarRect.width
	const seekTo = Number(percentage.toFixed(2)) * duration.value
	const video = el.value
	video.currentTime = seekTo
}

const gradientOverlayStyles = computed(() => ({
	background: `linear-gradient(to top, rgba(0, 0, 0, 0.6) 0%, rgba(0, 0, 0, 0.1) 25%, rgba(0, 0, 0, 0) 100%)`,
}))

const resetProgress = () => {
	progress.value = 0
	isPlaying.value = false
}
</script>
