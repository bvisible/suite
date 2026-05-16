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
			class="h-svh overflow-y-auto p-4 pe-3 custom-scrollbar"
			:class="{ 'pb-14': !inReadonlyMode }"
			:style="scrollbarStyles"
		>
			<div :style="virtualContainerStyles">
				<div
					v-for="virtualRow in virtualRows"
					:key="virtualRow.key"
					:class="getVirtualRowWrapperClasses(virtualRow.index)"
					:style="getVirtualRowWrapperStyles(virtualRow)"
					@click="handleSlideClick(virtualRow.index)"
				>
					<ThumbnailContainer
						:slide="slides[virtualRow.index]"
						:isActive="isSlideActive(virtualRow.index)"
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

import ThumbnailContainer from '@/components/ThumbnailContainer.vue'
import { useNavigationPanel } from '@/composables/useNavigationPanel'

import { slides, slideIndex, focusedSlide } from '@/stores/slide'
import { handleScrollBarWheelEvent } from '@/utils/helpers'

import { useVirtualizer } from '@tanstack/vue-virtual'
import { commandHistory } from '@/stores/historyMeta'
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
	if (typeof slide === 'number') {
		return slideIndex.value === slide
	}
	return slideIndex.value == slides.value.indexOf(slide)
}

const getVirtualRowWrapperClasses = (index) => [
	'virtual-row-wrapper',
	{ 'is-active': isSlideActive(index) },
]

const handleSlideClick = async (index) => {
	if (isSlideActive(index) && !inReadonlyMode.value) {
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

const scrollToVirtualItem = (index) => {
	rowVirtualizer.value.scrollToIndex(index, {
		align: 'center',
		behavior: 'smooth',
	})
}

const isItemFullyVisible = (scrollElement, virtualItem) => {
	const viewportTop = scrollElement.scrollTop
	const viewportBottom = viewportTop + scrollElement.clientHeight

	const itemTop = virtualItem.start
	const itemBottom = virtualItem.end

	return itemTop >= viewportTop && itemBottom <= viewportBottom
}

const scrollToSlide = (index) => {
	const scrollElement = scrollableArea.value
	if (!scrollElement) return

	const virtualItem = rowVirtualizer.value.getVirtualItems().find((v) => v.index === index)
	if (!virtualItem) {
		// item is not rendered by virtual list so scroll directly without checking visibility
		return scrollToVirtualItem(index)
	}

	const fullyVisible = isItemFullyVisible(scrollElement, virtualItem)
	if (!fullyVisible) {
		scrollToVirtualItem(index)
	}
}

watch(
	() => slideIndex.value,
	(index) => {
		if (!isNavigationPanelOpen.value) return
		scrollToSlide(index)
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

const virtualContainerStyles = computed(() => ({
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
.virtual-row-wrapper.is-active::before {
	content: '';
	position: absolute;
	left: -1.25rem;
	top: 0;
	width: 0.5rem;
	height: 90px;
	border-radius: 0 0.25rem 0.25rem 0;
	background: rgb(59 130 246 / 0.9);
	pointer-events: none;
}
</style>
