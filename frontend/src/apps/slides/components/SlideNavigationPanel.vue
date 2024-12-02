<template>
	<!-- Slide Navigation Panel -->
	<div
		id="slide-navigation-panel"
		class="fixed z-20 h-[94.27%] w-44 select-none border-r bg-white shadow-2xl shadow-gray-300 transition-all duration-500 ease-in-out hover:overflow-y-auto"
		:class="showNavigator ? 'left-0' : '-left-44'"
		v-if="presentation.data?.slides"
		@mouseenter="showCollapseShortcut = true"
		@mouseleave="showCollapseShortcut = false"
	>
		<div class="flex flex-col px-4">
			<Draggable v-model="presentation.data.slides" item-key="name" :force-fallback="true">
				<template #item="{ element: slide }">
					<img
						:src="slide.thumbnail"
						class="my-4 h-20 cursor-pointer rounded"
						:class="
							activeSlideIndex == slide.idx - 1
								? 'ring-2 ring-blue-400 ring-offset-1'
								: 'border border-gray-300'
						"
						@click="activeSlideIndex = slide.idx - 1"
					/>
				</template>
			</Draggable>

			<div
				class="flex h-20 cursor-pointer items-center justify-center rounded border border-dashed border-gray-400 shadow-lg shadow-gray-100 hover:border-blue-400 hover:bg-blue-50"
				@click="addSlide"
			>
				<FeatherIcon name="plus" class="h-3.5 text-gray-600" />
			</div>
		</div>

		<div
			v-if="showNavigator && showCollapseShortcut"
			class="fixed -left-0.5 bottom-0 z-20 flex h-10 w-44 cursor-pointer items-center justify-between border-t bg-white p-4"
			@click="showNavigator = !showNavigator"
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
			class="top-[calc(50% - 24)px] fixed left-0 z-20 flex h-12 w-4 cursor-pointer items-center justify-center rounded-r-lg border bg-white drop-shadow-xl"
			@click="showNavigator = !showNavigator"
		>
			<FeatherIcon name="chevron-left" class="h-3 pe-1" />
		</div>
	</div>
</template>

<script setup>
import { ref, onBeforeMount, onBeforeUnmount } from 'vue'
import Draggable from 'vuedraggable'

import { call } from 'frappe-ui'

import { activeSlideIndex, presentation } from '@/stores/slide'

const showNavigator = ref(true)
const showCollapseShortcut = ref(false)

const updateActiveSlide = (e) => {
	switch (e.key) {
		case 'ArrowDown':
			if (activeSlideIndex.value < presentation.data.slides.length - 1) {
				activeSlideIndex.value += 1
			}
			break

		case 'ArrowUp':
			if (activeSlideIndex.value > 0) {
				activeSlideIndex.value -= 1
			}
			break
	}

	if (e.metaKey && e.key === 'b') {
		showNavigator.value = !showNavigator.value
	}
}

const addSlide = async () => {
	await call('frappe.client.insert', {
		doc: {
			doctype: 'Slide',
			parenttype: 'Presentation',
			parentfield: 'slides',
			parent: presentation.data.name,
		},
	})
	await presentation.reload()
	activeSlideIndex.value = presentation.data.slides.length
}

onBeforeMount(() => {
	window.addEventListener('keydown', updateActiveSlide, null)
})

onBeforeUnmount(() => {
	window.removeEventListener('keydown', updateActiveSlide)
})
</script>

<style scoped>
.ghost {
	display: none;
}
</style>
