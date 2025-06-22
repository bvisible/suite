<template>
	<!-- Slide Navigation Panel -->
	<div
		:class="[panelClasses, attrs.class]"
		@mouseenter="handleHoverChange"
		@mouseleave="handleHoverChange"
		@wheel="handleWheelEvent"
	>
		<div
			v-if="presentation.data"
			class="flex h-full flex-col overflow-y-auto p-4"
			:style="scrollbarStyles"
		>
			<Draggable v-model="presentation.data.slides" item-key="name" @end="handleSortEnd">
				<template #item="{ element: slide }">
					<div
						:class="getThumbnailClasses(slide)"
						:style="getThumbnailStyles(slide)"
						@click="emit('changeSlide', slide.idx - 1)"
						:ref="(el) => (slideThumbnailsRef[slide.idx - 1] = el)"
					></div>
				</template>
			</Draggable>

			<div
				:class="insertButtonClasses"
				@click="emit('insertSlide', presentation.data.slides.length - 1)"
			>
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
		<LucideChevronRight class="size-3.5" />
	</div>
</template>

<script setup>
import { ref, computed, watch, nextTick, useTemplateRef } from 'vue'

import { call } from 'frappe-ui'

import Draggable from 'vuedraggable'

import { presentation } from '@/stores/presentation'
import { slide, slideIndex } from '@/stores/slide'

import { useAttrs } from 'vue'

const attrs = useAttrs()

const showNavigator = defineModel('showNavigator', {
	type: Boolean,
	default: true,
})

const emit = defineEmits(['changeSlide', 'insertSlide'])

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

const getThumbnailClasses = (slide) => {
	const baseClasses =
		'my-4 first:mt-0 w-full aspect-video cursor-pointer rounded bg-center bg-no-repeat bg-cover border'
	const borderClasses =
		slide.idx - 1 == slideIndex.value ? 'border-2 border-blue-400' : 'border border-gray-300'
	return `${baseClasses} ${borderClasses}`
}

const getThumbnailStyles = (s) => {
	const img = slideIndex.value == s.idx - 1 ? slide.value.thumbnail : s.thumbnail
	return {
		backgroundImage: `url(${img})`,
	}
}

const toggleButtonClasses = computed(() => {
	const baseClasses = 'z-20 flex cursor-pointer items-center border bg-white'
	if (showNavigator.value) {
		return `${baseClasses} fixed -left-0.4 bottom-0 h-10 w-48 justify-between p-4`
	}
	return `${baseClasses} absolute top-1/2 transform -transform-y-1/2 h-12 w-4 justify-center rounded-r-lg shadow-xl`
})

const handleSortEnd = async (event) => {
	const data = presentation.data
	emit('changeSlide', event.newIndex)
	data.slides.forEach((slide) => {
		slide.idx = data.slides.indexOf(slide) + 1
	})
	await call('frappe.client.save', {
		doc: data,
	})
	await presentation.reload()
}

const handleWheelEvent = (e) => {
	// allow normal scroll behaviour
	if (!e.ctrlKey && !e.metaKey) return

	// prevent zoom event from triggering
	e.preventDefault()
	e.stopPropagation()
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

const handleScrollChange = (index) => {
	const el = slideThumbnailsRef.value[index]

	if (!el) return
	el.scrollIntoView({
		behavior: 'smooth',
		block: 'start',
		inline: 'nearest',
	})
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

::-webkit-scrollbar {
	width: 4px;
}

::-webkit-scrollbar-thumb {
	background-color: var(--scrollbar-thumb-color);
	border-radius: 20px;
}

::-webkit-scrollbar-thumb:hover {
	background-color: #c6c6c6;
}
</style>
