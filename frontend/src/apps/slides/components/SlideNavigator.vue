<template>
	<!-- Slide Navigation Panel -->
	<div
		class="fixed z-20 h-[743px] w-44 overflow-y-auto border-r bg-white shadow-xl shadow-gray-200 transition-all duration-500 ease-in-out"
		:class="showNavigator ? 'left-0' : '-left-44'"
	>
		<div class="flex flex-col gap-4 p-4">
			<div
				v-for="i in presentation?.slides.length"
				:key="i"
				class="h-20 cursor-pointer rounded border shadow-lg shadow-gray-100"
				:class="activeSlide == i ? 'border-gray-500' : 'border-gray-300'"
				@click="activeSlide = i"
			>
				<div class="p-1 text-xs text-gray-500">{{ i }}</div>
			</div>

			<div
				class="flex h-20 cursor-pointer items-center justify-center rounded border border-dashed border-gray-400 shadow-lg shadow-gray-100 hover:bg-gray-50"
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
import { ref } from 'vue'

import { PanelLeftOpen, PanelLeftClose } from 'lucide-vue-next'

defineProps({
	presentation: Object,
})

const activeSlide = defineModel('activeSlide', {
	type: Number,
	default: 1,
})

const showNavigator = ref(false)
</script>
