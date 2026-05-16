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
			class="h-svh space-x-2 overflow-y-auto overflow-x-hidden p-4 pe-3 custom-scrollbar"
			:class="{ 'pb-14': !inReadonlyMode }"
			:style="scrollbarStyles"
		>
			<div :style="virtualRowContainerStyles">
				<div
					v-for="virtualRow in virtualRows"
					:key="virtualRow.key"
					class="virtual-row-wrapper"
					:style="getVirtualRowWrapperStyles(virtualRow)"
				>
					<ThumbnailContainer
						:slide="slides[virtualRow.index]"
						:isActive="isSlideActive(slides[virtualRow.index])"
					/>
				</div>
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

import ThumbnailContainer from '@/components/ThumbnailContainer.vue'
import { useNavigationPanel } from '@/composables/useNavigationPanel'

import { slides, slideIndex, currentSlide, focusedSlide } from '@/stores/slide'
import { handleScrollBarWheelEvent, getThumbnailCardStyles } from '@/utils/helpers'

import { useVirtualizer } from '@tanstack/vue-virtual'
import { commandHistory, recentlyRestored } from '@/stores/historyMeta'
import { reorderSlidesCommand } from '@/stores/commands'
import { resetFocus } from '@/stores/element'

const attrs = useAttrs()

const scrollableArea = useTemplateRef('scrollableArea')

const { isNavigationPanelOpen, toggleNavigationPanel } = useNavigationPanel()

const inReadonlyMode = inject('inReadonlyMode', ref(false))

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

const ROW_HEIGHT = 90

const rowVirtualizer = useVirtualizer(
	computed(() => ({
		count: slides.value.length,
		getScrollElement: () => scrollableArea.value,
		estimateSize: () => ROW_HEIGHT + 16, // row height + margin
		overscan: 3,
	})),
)

const virtualRows = computed(() => rowVirtualizer.value.getVirtualItems())
const totalSize = computed(() => rowVirtualizer.value.getTotalSize())

const virtualRowContainerStyles = computed(() => ({
	height: `${totalSize.value}px`,
	width: '100%',
	position: 'relative',
}))

const getVirtualRowWrapperStyles = (virtualRow) => ({
	position: 'absolute',
	top: 0,
	left: 0,
	width: '100%',
	height: `${virtualRow.size}px`,
	transform: `translateY(${virtualRow.start}px)`,
})
</script>

<style scoped>
.sortable-ghost {
	opacity: 1;
}

.sortable-chosen {
	opacity: 0.8;
}
</style>
