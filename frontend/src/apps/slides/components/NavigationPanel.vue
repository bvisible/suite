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
			class="flex h-full flex-col overflow-y-auto p-4 pb-14 custom-scrollbar"
			:style="scrollbarStyles"
		>
			<Draggable v-model="slides" item-key="name" @end="handleSortEnd">
				<template #item="{ element: slide }">
					<div
						:class="getThumbnailClasses(slide)"
						:style="getThumbnailStyles(slide)"
						@click="handleSlideClick(slide)"
						:ref="(el) => (slideThumbnailsRef[slides.indexOf(slide)] = el)"
					></div>
				</template>
			</Draggable>

			<div :class="insertButtonClasses" @click="emit('openLayoutDialog')">
				<LucidePlus class="size-3.5" />
			</div>
		</div>

		<div
			v-if="showNavigator && showCollapseShortcut"
			:class="toggleButtonClasses"
			@click="toggleNavigator"
		>
			<div class="text-2xs text-gray-500">Toggle Sidebar</div>
			<div class="flex h-5 w-1/3 items-center justify-center rounded-sm border bg-gray-100">
				<div class="text-xs text-gray-500">⌘ + B</div>
			</div>
		</div>
	</div>

	<!-- Slide Navigator Toggle -->
	<div v-if="!showNavigator" :class="toggleButtonClasses" @click="toggleNavigator">
		<LucideChevronRight class="size-3.5 text-gray-500" />
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useTemplateRef } from 'vue'

import { call } from 'frappe-ui'

import Draggable from 'vuedraggable'

import { slides, slideIndex, currentSlide, focusedSlide } from '@/stores/slide'
import { handleScrollBarWheelEvent } from '@/utils/helpers'

import { useAttrs } from 'vue'
import { ignoreUpdates } from '@/stores/presentation'

const attrs = useAttrs()

const scrollableArea = useTemplateRef('scrollableArea')

const showNavigator = defineModel('showNavigator', {
	type: Boolean,
	default: true,
})

const props = defineProps({
	recentlyRestored: {
		type: Boolean,
		default: false,
	},
})

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
	if (isSlideActive(slide)) {
		focusedSlide.value = slideIndex.value
		return
	}
	emit('changeSlide', slides.value.indexOf(slide))
}

const getThumbnailClasses = (slide) => {
	const baseClasses =
		'my-4 first:mt-0 w-full aspect-video cursor-pointer rounded bg-center bg-no-repeat bg-cover border transition-all duration-400 ease-in-out'

	const isActive = isSlideActive(slide)
	const isFocused = focusedSlide.value == slides.value.indexOf(slide)

	let outlineClasses = ''
	if (isFocused) {
		outlineClasses += 'ring-blue-300 ring-2 ring-offset-1'
	} else if (isActive && props.recentlyRestored) {
		outlineClasses += 'ring-blue-200 ring-[2px] ring-offset-2 scale-[1.01]'
	} else if (isActive) {
		outlineClasses += 'ring-gray-400 ring-[1.5px] ring-offset-1'
	} else {
		outlineClasses += 'ring-white hover:border-gray-300'
	}

	return `${baseClasses} ${outlineClasses}`
}

const getThumbnailStyles = (s) => {
	return {
		backgroundImage: `url(${s.thumbnail})`,
		// intentional to reduce extreme color change while loading new thumbnail which might be visually distracting
		backgroundColor: currentSlide.value?.background || '#ffffff', //fallback color
	}
}

const toggleButtonClasses = computed(() => {
	const baseClasses = 'flex cursor-pointer items-center border bg-white'
	if (showNavigator.value) {
		return `${baseClasses} fixed -left-0.4 bottom-0 h-10 w-48 justify-between p-4`
	}
	return `${baseClasses} absolute top-1/2 transform -transform-y-1/2 h-12 w-4 justify-center rounded-r-lg shadow-xl`
})

const handleSortEnd = async (event) => {
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

	const isScrollable = scrollableArea.value.scrollHeight > scrollableArea.value.clientHeight

	if (isScrollable) {
		// adjust offset for top padding - 16px
		const offset = element.offsetTop - scrollableArea.value.offsetTop - 16

		scrollableArea.value.scrollTo({
			top: offset,
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
