<template>
	<!-- Slide Navigation Panel -->
	<div
		id="slide-navigation-panel"
		class="fixed z-20 h-[94.2%] w-44 border-r bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out hover:overflow-y-auto"
		:class="showNavigator ? 'left-0' : '-left-44'"
		v-if="presentation.data?.slides"
	>
		<div class="flex flex-col gap-4 p-4">
			<img
				:src="presentation.data.slides[i - 1].thumbnail"
				v-for="i in presentation.data.slides.length"
				:key="i"
				class="h-20 cursor-pointer rounded"
				:class="
					activeSlideIndex == i
						? 'ring-[1.8px] ring-blue-400 ring-offset-[0px]'
						: 'border border-gray-300'
				"
				@click="activeSlideIndex = i"
			/>

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
import { useRoute } from 'vue-router'

import { call } from 'frappe-ui'

import { PanelLeftOpen, PanelLeftClose } from 'lucide-vue-next'
import { activeSlideIndex, presentation } from '@/stores/slide'

const route = useRoute()

const showNavigator = ref(false)

const updateActiveSlide = (e) => {
	switch (e.key) {
		case 'ArrowDown':
			if (activeSlideIndex.value < presentation.data.slides.length) {
				activeSlideIndex.value += 1
			}
			break

		case 'ArrowUp':
			if (activeSlideIndex.value > 1) {
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
			parent: route.params.name,
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
