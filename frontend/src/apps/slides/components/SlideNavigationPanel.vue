<template>
	<!-- Slide Navigation Panel -->
	<div
		id="slide-navigation-panel"
		class="fixed z-20 h-[94.27%] w-44 select-none border-r bg-white shadow-2xl shadow-gray-300 transition-all duration-500 ease-in-out hover:overflow-y-auto"
		:class="showNavigator ? 'left-0' : '-left-44'"
		v-if="presentation.data?.slides"
	>
		<div class="flex flex-col px-4">
			<Draggable v-model="presentation.data.slides" item-key="name" :force-fallback="true">
				<template #item="{ element: slide }">
					<img
						:src="slide.thumbnail"
						class="my-4 h-20 cursor-pointer rounded"
						:class="
							activeSlideIndex == slide.idx
								? 'ring-2 ring-blue-400 ring-offset-1'
								: 'border border-gray-300'
						"
						@click="activeSlideIndex = slide.idx"
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
	</div>

	<!-- Slide Navigator Toggle -->
	<div
		class="fixed z-10 flex h-8 w-8 cursor-pointer items-center justify-center transition-all duration-500 ease-in-out"
		:class="
			showNavigator
				? 'bottom-2 left-44'
				: 'bottom-2 left-2 rounded bg-white shadow-md shadow-gray-400'
		"
		@click="showNavigator = !showNavigator"
	>
		<PanelLeftClose v-if="showNavigator" size="16" strokeWidth="1.5" />
		<PanelLeftOpen v-else size="16" strokeWidth="1.5" />
	</div>
</template>

<script setup>
import { ref, onBeforeMount, onBeforeUnmount } from 'vue'
import Draggable from 'vuedraggable'

import { call } from 'frappe-ui'

import { PanelLeftOpen, PanelLeftClose } from 'lucide-vue-next'
import { activeSlideIndex, presentation } from '@/stores/slide'

const showNavigator = ref(false)

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
