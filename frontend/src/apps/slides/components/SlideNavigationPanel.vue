<template>
	<!-- Slide Navigation Panel -->
	<div
		class="fixed z-20 h-[94.27%] w-44 border-r bg-white shadow-2xl shadow-gray-300 transition-all duration-500 ease-in-out hover:overflow-y-auto"
		:class="showNavigator ? 'left-0' : '-left-44'"
		@mouseenter="showCollapseShortcut = true"
		@mouseleave="showCollapseShortcut = false"
		@wheel.prevent="(e) => e.stopPropagation()"
	>
		<div class="flex flex-col px-4">
			<Draggable v-model="presentation.data.slides" item-key="name" @end="handleSortEnd">
				<template #item="{ element: slide }">
					<div
						class="my-4 h-20 cursor-pointer rounded bg-center bg-no-repeat bg-cover border"
						:class="getThumbnailClasses(slide)"
						:style="getThumbnailStyles(slide)"
						@click="changeSlide(slide.idx - 1)"
					></div>
				</template>
			</Draggable>

			<div
				class="flex h-20 cursor-pointer items-center justify-center rounded border border-dashed border-gray-400 shadow-lg shadow-gray-100 hover:border-blue-400 hover:bg-blue-50"
				@click="insertSlide(presentation.data.slides.length)"
			>
				<FeatherIcon name="plus" class="h-3.5 text-gray-600" />
			</div>
		</div>

		<div
			v-if="showNavigator && showCollapseShortcut"
			class="fixed -left-0.5 bottom-0 z-20 flex h-10 w-44 cursor-pointer items-center justify-between border-t bg-white p-4"
			@click="toggleNavigator"
		>
			<div class="text-2xs text-gray-500">Toggle</div>
			<div class="flex h-5 w-1/3 items-center justify-center rounded-sm border bg-gray-100">
				<div class="text-xs text-gray-500">⌘ + B</div>
			</div>
		</div>
	</div>

	<!-- Slide Navigator Toggle -->
	<div v-if="!showNavigator">
		<div
			class="top-[calc(50% - 24)px] fixed left-0 z-20 flex h-12 w-4 cursor-pointer items-center justify-center rounded-r-lg border bg-white shadow-xl"
			@click="toggleNavigator"
		>
			<FeatherIcon name="chevron-right" class="h-3 pe-1" />
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'

import { call } from 'frappe-ui'

import Draggable from 'vuedraggable'

import { presentation } from '@/stores/presentation'
import { slideIndex, changeSlide, insertSlide, slide } from '@/stores/slide'

const showNavigator = defineModel('showNavigator', {
	type: Boolean,
	default: true,
})

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
	changeSlide(event.newIndex)
	data.slides.forEach((slide) => {
		slide.idx = data.slides.indexOf(slide) + 1
	})
	await call('frappe.client.save', {
		doc: data,
	})
	await presentation.reload()
}
</script>

<style scoped>
.sortable-ghost {
	opacity: 1;
}

.sortable-chosen {
	opacity: 0.8;
}
</style>
