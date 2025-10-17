<template>
	<div @click="handleVideoClick" @mouseenter="handleHoverChange" @mouseleave="handleHoverChange">
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
			:poster="`/api/method/slides.api.file.get_media_file?src=${videoPoster}&public=${isPublicPresentation}`"
		>
			<source
				:src="`/api/method/slides.api.file.get_media_file?src=${videoSrc}&public=${isPublicPresentation}`"
			/>
		</video>
		<div
			ref="overlay"
			v-show="showOverlay"
			class="overlay absolute left-0 top-0 size-full cursor-default overflow-hidden transition-opacity duration-500 ease-in-out"
			:style="gradientOverlayStyles"
		>
			<div v-if="showProgressBar" :class="toggleButtonClasses">
				<component
					size="16"
					:is="isPlaying ? Pause : Play"
					class="stroke-[1.5] ps-[0.5px] text-white"
				/>
			</div>
			<div
				v-if="showProgressBar"
				ref="progressBar"
				:class="progressBarClasses"
				@click.stop="seekTimestamp"
			>
				<div :class="getBarClasses('duration')"></div>
				<div :class="getBarClasses('current')" :style="{ width: `${progress}%` }"></div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref, computed, useTemplateRef, inject } from 'vue'

import { Play, Pause } from 'lucide-vue-next'

import { inSlideShow, isPublicPresentation, readonlyMode } from '@/stores/presentation'
import { activeElementIds } from '@/stores/element'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const el = useTemplateRef('videoElement')
const overlay = useTemplateRef('overlay')

const videoSrc = computed(() => {
	if (element.value.src.startsWith('/private')) return element.value.src
	return `/private${element.value.src}`
})

const videoPoster = computed(() => {
	if (element.value.poster.startsWith('/private')) return element.value.poster
	return `/private${element.value.poster}`
})

const toggleButtonClasses =
	'absolute inset-[calc(50%-16px)] flex size-8 cursor-pointer items-center justify-center rounded-lg bg-white-overlay-200 opacity-95'

const getBarClasses = (type) => {
	const commonClasses = 'bg-white-overlay-900 h-full absolute left-0 top-0'
	if (type == 'current') {
		return `${commonClasses} opacity-80 transition-width duration-100 ease-linear`
	}
	return `${commonClasses} opacity-30 w-full`
}

const progressBarClasses = computed(() => {
	const baseClasses = 'absolute w-full bottom-0 left-0 cursor-pointer h-2'
	return `${baseClasses} ${inSlideShow.value ? 'bottom-0' : 'bottom-[10px]'}`
})

const isPlaying = ref(false)

const videoStyle = computed(() => ({
	width: '100%',
	opacity: element.value.opacity / 100,
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
		if (inSlideShow.value) showOverlay.value = false
	} else {
		isPlaying.value = false
		video.pause()
		if (inSlideShow.value) showOverlay.value = true
	}
}

const handleVideoClick = (e) => {
	const isActive = activeElementIds.value.includes(element.value.id)

	// in slideshow, always toggle playing on click anywhere
	// in editor, toggle playing only when center play button is clicked

	if (readonlyMode.value || inSlideShow.value || (isActive && e.target !== overlay.value)) {
		e.stopPropagation()
		togglePlaying()
	}
}

const duration = ref(0)
const progress = ref(0)

const updateProgress = () => {
	const video = el.value
	if (!video || !duration.value) return
	progress.value = Math.round((video.currentTime / duration.value) * 100)
}

const updateDuration = () => {
	const video = el.value
	if (!video || !video.duration) return
	duration.value = video.duration
}

const hoverOver = ref(false)

const showProgressBar = computed(() => {
	// In editor, show it when video is active
	const isActive = activeElementIds.value.includes(element.value.id)

	// During slideshow, show it only if user is hovering over video
	const slideshowHovering = inSlideShow.value && hoverOver.value

	return isActive || slideshowHovering || (readonlyMode.value && !inSlideShow.value)
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
	background: `radial-gradient(circle at center, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0.1) 5%, rgba(0, 0, 0, 0) 100%),
        linear-gradient(to top, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0.1) 15%, rgba(0, 0, 0, 0) 100%)`,
	opacity: showProgressBar.value ? 1 : 0,
	borderRadius: `${element.value.borderRadius}px`,
}))

const resetProgress = () => {
	progress.value = 0
	isPlaying.value = false
}

const handleHoverChange = (e) => {
	if (e.type === 'mouseenter') {
		hoverOver.value = true
	} else if (e.type === 'mouseleave') {
		hoverOver.value = false
	}
}

const showOverlay = ref(inSlideShow.value ? false : true)
</script>
