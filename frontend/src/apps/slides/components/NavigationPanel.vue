<template>
	<!-- Slide Navigation Panel -->
	<div
		:class="[panelClasses, attrs.class]"
		@mouseenter="handleHoverChange"
		@mouseleave="handleHoverChange"
		@wheel="handleScrollBarWheelEvent"
		@click.stop
	>
		<div
			ref="scrollableArea"
			v-if="slides"
			class="flex h-full flex-col overflow-y-auto p-4 custom-scrollbar"
			:class="{ 'pb-14': !props.readonlyMode }"
			:style="scrollbarStyles"
		>
			<template v-if="props.readonlyMode">
				<div
					v-for="slide in slides"
					:key="slide.name"
					:class="getThumbnailClasses(slide)"
					:style="getThumbnailStyles(slide)"
					@click="handleSlideClick(slide)"
					:ref="(el) => (slideThumbnailsRef[slides.indexOf(slide)] = el)"
				>
					<div
						class="absolute inset-0 flex justify-between rounded p-2"
						:style="getGradientOverlayStyles(slide)"
					>
						<div class="text-[10px] font-medium">{{ slide.idx }}</div>
						<TransitionIcon v-if="slide.transition != 'None'" class="h-3 opacity-80" />
					</div>

					<div
						v-if="isSlideActive(slide)"
						class="absolute -left-5 h-full w-2 rounded-r bg-blue-500 opacity-90"
					></div>
				</div>
			</template>

			<template v-else>
				<Draggable
					v-model="slides"
					item-key="name"
					@start="handleSortStart"
					@end="handleSortEnd"
				>
					<template #item="{ element: slide }">
						<div
							:class="getThumbnailClasses(slide)"
							:style="getThumbnailStyles(slide)"
							@click="handleSlideClick(slide)"
							:ref="(el) => (slideThumbnailsRef[slides.indexOf(slide)] = el)"
						>
							<div
								class="absolute inset-0 flex justify-between rounded p-2"
								:style="getGradientOverlayStyles(slide)"
							>
								<div class="text-[10px] font-medium">{{ slide.idx }}</div>
								<TransitionIcon
									v-if="slide.transition != 'None'"
									class="h-3 opacity-80"
								/>
							</div>

							<div
								v-if="isSlideActive(slide)"
								class="absolute -left-5 h-full w-2 rounded-r bg-blue-500 opacity-90"
							></div>
						</div>
					</template>
				</Draggable>

				<div :class="insertButtonClasses" @click="emit('openLayoutDialog')">
					<LucidePlus class="size-3.5" />
				</div>
			</template>
		</div>
	</div>

	<!-- Slide Navigator Toggle -->
	<div v-if="!showNavigator" :class="toggleButtonClasses" @click="toggleNavigator">
		<LucideChevronRight class="size-3.5 text-gray-500" />
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useTemplateRef, useAttrs } from 'vue'

import Draggable from 'vuedraggable'

import TransitionIcon from '@/icons/TransitionIcon.vue'

import { slides, slideIndex, currentSlide, focusedSlide } from '@/stores/slide'
import { handleScrollBarWheelEvent, getThumbnailCardStyles } from '@/utils/helpers'
import { isBackgroundColorDark } from '@/utils/color'

import { ignoreUpdates, historyMetadata } from '@/stores/presentation'
import { resetFocus } from '@/stores/element'

const attrs = useAttrs()

const scrollableArea = useTemplateRef('scrollableArea')

const showNavigator = defineModel('showNavigator', {
	type: Boolean,
	default: true,
})

const props = defineProps({
	readonlyMode: {
		type: Boolean,
		default: false,
	},
	recentlyRestored: {
		type: Boolean,
		default: false,
	},
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

const emit = defineEmits(['changeSlide', 'openLayoutDialog'])

const insertButtonClasses =
	'flex w-full aspect-video cursor-pointer items-center justify-center rounded border border-dashed border-gray-400 hover:border-blue-400 hover:bg-blue-50'

const showCollapseShortcut = ref(false)

const toggleNavigator = () => {
	showNavigator.value = !showNavigator.value
}

const panelClasses = computed(() => {
	// can't add it from parent attrs.class since attrs is not reactive
	const positionClass = showNavigator.value ? 'left-0' : '-left-48'
	const baseClasses = [
		'w-48',
		'border-r',
		'bg-white',
		'transition-all',
		'duration-300',
		'ease-in-out',
	]
	return [...baseClasses, positionClass]
})

const isSlideActive = (slide) => {
	return slideIndex.value == slides.value.indexOf(slide)
}

const handleSlideClick = async (slide) => {
	const index = slides.value.indexOf(slide)
	if (isSlideActive(slide) && !props.readonlyMode) {
		resetFocus()
		focusedSlide.value = index
		return
	}
	emit('changeSlide', index)
}

const getThumbnailClasses = (slide) => {
	const baseClasses =
		'relative mb-4 first:mt-0 w-full aspect-video cursor-pointer rounded bg-center bg-no-repeat bg-cover border transition-all duration-400 ease-in-out'

	const isActive = isSlideActive(slide)
	const isFocused = focusedSlide.value == slides.value.indexOf(slide)

	let outlineClasses = ''
	if (isFocused) {
		outlineClasses += 'ring-blue-500 ring-2 ring-offset-1'
	} else if (isActive && props.recentlyRestored) {
		outlineClasses += 'ring-blue-500 ring-[2px] ring-offset-2 scale-[1.01]'
	} else if (isActive) {
		outlineClasses += 'ring-gray-400 ring-[1.5px] ring-offset-0.5'
	} else {
		outlineClasses += 'ring-white hover:border-gray-300'
	}

	return `${baseClasses} ${outlineClasses}`
}

const getThumbnailStyles = (s) => {
	let styles = getThumbnailCardStyles(s.thumbnail)

	// intentional to reduce extreme color change while loading new thumbnail which might be visually distracting
	styles.backgroundColor = s.background || '#ffffff' //fallback color

	return styles
}

const toggleButtonClasses = computed(() => {
	const baseClasses = 'flex cursor-pointer items-center border bg-white'
	if (showNavigator.value) {
		return `${baseClasses} fixed -left-0.4 bottom-0 h-10 w-48 justify-between p-4`
	}
	return `${baseClasses} absolute top-1/2 transform -transform-y-1/2 h-12 w-4 justify-center rounded-r-lg shadow-xl`
})

const handleSortStart = (event) => {
	historyMetadata.focusIndexPostUndo = event.oldIndex
	resetFocus()
}

const handleSortEnd = async (event) => {
	historyMetadata.focusIndexPostRedo = event.newIndex
	ignoreUpdates(() => {
		slides.value.forEach((slide, index) => {
			slide.idx = index + 1
		})
	})
	emit('changeSlide', event.newIndex)
}

const handleHoverChange = (e) => {
	if (e.type === 'mouseenter') {
		showCollapseShortcut.value = true
	} else if (e.type === 'mouseleave') {
		showCollapseShortcut.value = false
	}
}

const scrollbarStyles = computed(() => ({
	'--scrollbar-thumb-color': showCollapseShortcut.value ? '#cfcfcf' : 'transparent',
}))

const slideThumbnailsRef = ref([])

const scrollThumbnailToView = (element) => {
	if (!scrollableArea.value) return

	const areaTop = scrollableArea.value.scrollTop
	const areaHeight = scrollableArea.value.clientHeight
	const thumbnailTop = element.offsetTop - scrollableArea.value.offsetTop
	const thumbnailHeight = element.offsetHeight
	const thumbnailBottom = thumbnailTop + thumbnailHeight

	// Only scroll if thumbnail is partially visible
	if (thumbnailTop < areaTop || thumbnailBottom > areaTop + areaHeight) {
		const targetScroll = thumbnailTop - areaHeight / 2 + thumbnailHeight / 2
		scrollableArea.value.scrollTo({
			top: targetScroll,
			behavior: 'smooth',
		})
	}
}

const handleScrollChange = (index) => {
	const el = slideThumbnailsRef.value[index]

	if (!el) return
	scrollThumbnailToView(el)
}

watch(
	() => slideIndex.value,
	() => {
		if (!showNavigator.value) return
		nextTick(() => {
			handleScrollChange(slideIndex.value)
		})
	},
)
</script>

<style scoped>
.sortable-ghost {
	opacity: 1;
}

.sortable-chosen {
	opacity: 0.8;
}
</style>
