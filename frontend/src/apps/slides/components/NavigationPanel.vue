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
				></div>
			</template>

			<template v-else>
				<Draggable
					v-model="slides"
					item-key="name"
					@start="resetFocus"
					@end="handleSortEnd"
				>
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
			</template>
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
import { getAttachmentUrl } from '@/utils/mediaUploads'

import { useAttrs } from 'vue'
import { ignoreUpdates, isPublicPresentation } from '@/stores/presentation'
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
		'mb-4 first:mt-0 w-full aspect-video cursor-pointer rounded bg-center bg-no-repeat bg-cover border transition-all duration-400 ease-in-out'

	const isActive = isSlideActive(slide)
	const isFocused = focusedSlide.value == slides.value.indexOf(slide)

	let outlineClasses = ''
	if (isFocused) {
		outlineClasses += 'ring-blue-300 ring-2 ring-offset-1'
	} else if (isActive && props.recentlyRestored) {
		outlineClasses += 'ring-blue-300 ring-[2px] ring-offset-2 scale-[1.01]'
	} else if (isActive) {
		outlineClasses += 'ring-gray-400 ring-[1.5px] ring-offset-1'
	} else {
		outlineClasses += 'ring-white hover:border-gray-300'
	}

	return `${baseClasses} ${outlineClasses}`
}

const getThumbnailStyles = (s) => {
	const thumbnailUrl = getAttachmentUrl(s.thumbnail)
	const bgImage = thumbnailUrl.startsWith('data:')
		? thumbnailUrl
		: `url(/api/method/slides.api.file.get_media_file?src=${thumbnailUrl}&public=${isPublicPresentation.value})`
	return {
		backgroundImage: bgImage,
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
