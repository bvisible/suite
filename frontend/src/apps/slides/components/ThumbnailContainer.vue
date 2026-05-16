<template>
	<div :class="getThumbnailClasses(slide)" :style="getThumbnailStyles(slide)">
		<div :style="thumbnailViewStyles">
			<SlideElement
				v-for="element in slide?.elements"
				:key="`export-${element.id}`"
				mode="export"
				:element="element"
				:data-index="element.id"
			/>
		</div>
		<div
			class="absolute inset-0 flex w-full justify-between rounded p-2"
			:style="getGradientOverlayStyles(slide)"
		>
			<div class="text-[10px] font-medium">{{ slide.idx }}</div>
			<TransitionIcon v-if="slide.transition != 'None'" class="h-3 opacity-80" />
		</div>
		<div
			v-if="isActive"
			class="absolute -left-5 h-full w-2 rounded-r bg-blue-500 opacity-90"
		></div>
	</div>
</template>

<script setup>
import { focusedSlide, slides } from '@/stores/slide'
import { recentlyRestored } from '@/stores/historyMeta'

import SlideElement from '@/components/SlideElement.vue'
import TransitionIcon from '@/icons/TransitionIcon.vue'

import { isBackgroundColorDark } from '@/utils/color'

const THUMBNAIL_SCALE = 160 / 960

const props = defineProps({
	slide: { type: Object, required: true },
	isActive: { type: Boolean, default: false },
})

const getGradientOverlayStyles = (slide) => {
	const hasDarkBg = isBackgroundColorDark(slide.background)
	const textColor = hasDarkBg ? '#ffffff' : '#00000090'
	const background = hasDarkBg
		? 'linear-gradient(140deg, rgba(255, 255, 255, 0.3) 0%, rgba(255, 255, 255, 0) 20%, rgba(0, 0, 0, 0) 100%)'
		: 'linear-gradient(140deg, rgba(0, 0, 0, 0.1) 0%, rgba(0, 0, 0, 0) 20%, rgba(0, 0, 0, 0) 100%)'

	return {
		background,
		color: textColor,
	}
}

const thumbnailViewStyles = {
	width: '960px',
	height: '540px',
	transformOrigin: 'top left',
	transform: `scale(${THUMBNAIL_SCALE})`,
	position: 'absolute',
	top: '0',
	left: '0',
}

const getThumbnailClasses = (slide) => {
	const baseClasses = [
		'relative',
		'first:mt-0',
		'my-8',
		'cursor-pointer',
		'border',
		'rounded',
		'transition-all',
		'duration-400',
		'ease-in-out',
		'overflow-hidden',
		'select-none',
	]

	const isActive = props.isActive
	const isFocused = focusedSlide.value == slides.value.indexOf(slide)

	let outlineClasses = []
	if (isFocused) {
		outlineClasses.push('ring-blue-500', 'ring-[2px]', 'ring-offset-2')
	} else if (isActive && recentlyRestored.value) {
		outlineClasses.push('ring-blue-500', 'ring-[2px]', 'ring-offset-2', 'scale-[1.02]')
	} else if (isActive) {
		outlineClasses.push('ring-gray-400', 'ring-[1.5px]', 'ring-offset-0.5')
	} else {
		outlineClasses.push('ring-white', 'hover:border-gray-300')
	}

	return [...baseClasses, ...outlineClasses].join(' ')
}

const getThumbnailStyles = (s) => ({
	backgroundColor: s.background || '#ffffff',
	height: `${540 * THUMBNAIL_SCALE}px`,
})
</script>
