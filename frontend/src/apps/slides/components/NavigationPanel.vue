<template>
	<!-- Slide Navigation Panel -->
	<div
		class="fixed z-20 h-[94.27%] w-48 border-r bg-white shadow-2xl shadow-gray-300 transition-all duration-300 ease-in-out"
		:class="showNavigator ? 'left-0' : '-left-48'"
		@mouseenter="showCollapseShortcut = true"
		@mouseleave="showCollapseShortcut = false"
		@wheel="handleWheelEvent"
	>
		<div class="flex flex-col h-full px-4 pb-12 overflow-y-auto" :style="scrollbarStyles">
			<Draggable v-model="presentation.data.slides" item-key="name" @end="handleSortEnd">
				<template #item="{ element: slide }">
					<div
						class="my-4 w-full aspect-video cursor-pointer rounded bg-center bg-no-repeat bg-cover border"
						:class="getThumbnailClasses(slide)"
						:style="getThumbnailStyles(slide)"
						@click="emit('changeSlide', slide.idx - 1)"
					></div>
				</template>
			</Draggable>

			<div
				class="flex w-full aspect-video cursor-pointer items-center justify-center rounded border border-dashed border-gray-400 shadow-lg shadow-gray-100 hover:border-blue-400 hover:bg-blue-50"
				@click="emit('insertSlide', presentation.data.slides.length - 1)"
			>
				<LucidePlus class="h-3.5 w-3.5" />
			</div>
		</div>

		<div
			v-if="showNavigator && showCollapseShortcut"
			class="fixed -left-0.4 bottom-0 z-20 flex h-10 w-48 cursor-pointer items-center justify-between border-t bg-white p-4"
			@click="toggleNavigator"
		>
			<div class="text-2xs text-gray-500">Toggle Sidebar</div>
			<div class="flex h-5 w-1/3 items-center justify-center rounded-sm border bg-gray-100">
				<div class="text-xs text-gray-500">⌘ + B</div>
			</div>
		</div>
	</div>

	<!-- Slide Navigator Toggle -->
	<div
		v-if="!showNavigator"
		class="top-[calc(50% - 24)px] fixed left-0 z-20 flex h-12 w-4 cursor-pointer items-center justify-center rounded-r-lg border bg-white shadow-xl"
		@click="toggleNavigator"
	>
		<LucideChevronRight class="h-3.5 w-3.5" />
	</div>
</template>

<script setup>
import { ref, computed } from 'vue'

import { call } from 'frappe-ui'

import Draggable from 'vuedraggable'

import { presentation } from '@/stores/presentation'
import { slide, slideIndex } from '@/stores/slide'

const showNavigator = defineModel('showNavigator', {
	type: Boolean,
	default: true,
})

const emit = defineEmits(['changeSlide', 'insertSlide'])

const showCollapseShortcut = ref(false)

const toggleNavigator = () => {
	showNavigator.value = !showNavigator.value
}

const getThumbnailClasses = (slide) => {
	return slide.idx - 1 == slideIndex.value ? 'border-2 border-blue-400' : 'border border-gray-300'
}

const getThumbnailStyles = (s) => {
	const img = slideIndex.value == s.idx - 1 ? slide.value.thumbnail : s.thumbnail
	return {
		backgroundImage: `url(${img})`,
	}
}

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

const scrollbarStyles = computed(() => ({
	'--scrollbar-thumb-color': showCollapseShortcut.value ? '#cfcfcf' : 'transparent',
}))
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
