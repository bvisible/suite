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
			v-if="sidebarSlidesList"
			class="h-full space-y-4 overflow-y-auto overflow-x-hidden p-4 pe-3 custom-scrollbar"
			:class="{ 'pb-14': !inReadonlyMode }"
			:style="scrollbarStyles"
		>
			<div
				v-for="slide in sidebarSlidesList"
				:key="slide.clientId"
				:class="getThumbnailClasses(slide)"
				:style="getThumbnailStyles(slide)"
				@click="handleSlideClick(slide)"
				:ref="(el) => (slideThumbnailsRef[sidebarSlidesList.indexOf(slide)] = el)"
			>
				<div :style="getThumbnailInnerStyles(slide)">
					<SlideElement
						v-for="element in slide?.elements"
						:key="`export-${element.id}`"
						mode="export"
						:element="element"
						:data-index="element.id"
					/>
				</div>
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
		</div>
	</div>

	<!-- Slide Navigator Toggle -->
	<div v-if="!isNavigationPanelOpen" :class="toggleButtonClasses" @click="toggleNavigationPanel">
		<LucideChevronRight class="size-3.5 text-gray-500" />
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useTemplateRef, useAttrs, inject } from 'vue'

import Draggable from 'vuedraggable'

import TransitionIcon from '@/icons/TransitionIcon.vue'
import SlideElement from '@/components/SlideElement.vue'

import { useNavigationPanel } from '@/composables/useNavigationPanel'

import { slides, slideIndex, currentSlide, focusedSlide } from '@/stores/slide'
import { handleScrollBarWheelEvent, getThumbnailCardStyles } from '@/utils/helpers'
import { isBackgroundColorDark } from '@/utils/color'

import { commandHistory, recentlyRestored } from '@/stores/historyMeta'
import { reorderSlidesCommand } from '@/stores/commands'
import { resetFocus } from '@/stores/element'

const attrs = useAttrs()

const scrollableArea = useTemplateRef('scrollableArea')

const { isNavigationPanelOpen, toggleNavigationPanel } = useNavigationPanel()

const inReadonlyMode = inject('inReadonlyMode', ref(false))

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

const panelClasses = computed(() => {
	// can't add it from parent attrs.class since attrs is not reactive
	const positionClass = isNavigationPanelOpen.value ? 'left-0' : '-left-48'
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
	if (isSlideActive(slide) && !inReadonlyMode.value) {
		resetFocus()
		focusedSlide.value = index
		return
	}
	emit('changeSlide', index)
}

const getThumbnailClasses = (slide) => {
	const baseClasses =
		'relative first:mt-0 cursor-pointer rounded border transition-all duration-400 ease-in-out overflow-hidden'

	const isActive = isSlideActive(slide)
	const isFocused = focusedSlide.value == slides.value.indexOf(slide)

	let outlineClasses = ''
	if (isFocused) {
		outlineClasses += 'ring-blue-500 ring-2 ring-offset-1'
	} else if (isActive && recentlyRestored.value) {
		outlineClasses += 'ring-blue-500 ring-[2px] ring-offset-2 scale-[1.02]'
	} else if (isActive) {
		outlineClasses += 'ring-gray-400 ring-[1.5px] ring-offset-0.5'
	} else {
		outlineClasses += 'ring-white hover:border-gray-300'
	}

	return `${baseClasses} ${outlineClasses}`
}

const THUMBNAIL_SCALE = 160 / 960

const getThumbnailStyles = (s) => {
	return {
		backgroundColor: s.background || '#ffffff',
		width: `${160}px`,
		height: `${540 * THUMBNAIL_SCALE}px`,
	}
}

const getThumbnailInnerStyles = () => ({
	width: '960px',
	height: '540px',
	transformOrigin: 'top left',
	transform: `scale(${THUMBNAIL_SCALE})`,
	position: 'absolute',
	top: '0',
	left: '0',
})

const toggleButtonClasses = computed(() => {
	const baseClasses = 'flex cursor-pointer items-center border bg-white'
	if (isNavigationPanelOpen.value) {
		return `${baseClasses} fixed -left-0.4 bottom-0 h-10 w-48 justify-between p-4`
	}
	return `${baseClasses} absolute top-1/2 transform -transform-y-1/2 h-12 w-4 justify-center rounded-r-lg shadow-xl`
})

const handleSortStart = (event) => {
	resetFocus()
}

const handleSortEnd = async (event) => {
	commandHistory.execute(
		reorderSlidesCommand({
			oldIndex: event.oldIndex,
			newIndex: event.newIndex,
		}),
	)
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
		if (!isNavigationPanelOpen.value) return
		nextTick(() => {
			handleScrollChange(slideIndex.value)
		})
	},
)

const sidebarSlidesList = ref(slides.value)

watch(
	slides,
	(newSlides) => {
		sidebarSlidesList.value = newSlides
	},
	{ deep: true },
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
