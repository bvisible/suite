<template>
	<div :style="styles" :class="indicatorClasses">
		<div v-if="type === 'text'">{{ Math.round(dimensions.width) }}</div>
		<template v-else>
			<div>{{ Math.round(dimensions.width) }} × {{ Math.round(dimensions.height) }}</div>
		</template>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { currentSlide } from '@/stores/slide'
import { isBackgroundColorDark } from '@/utils/color'

const props = defineProps({
	type: {
		type: String,
		default: null,
	},
	dimensions: {
		type: Object,
		default: () => ({}),
	},
	indicatorStyles: {
		type: Object,
		default: () => ({}),
	},
})

const styles = computed(() => ({
	position: 'absolute',
	zIndex: 5,
	...props.indicatorStyles,
}))

const indicatorClasses = computed(() => {
	const baseClasses = 'backdrop-blur-sm opacity-85 text-black'
	const bgClass = isBackgroundColorDark(currentSlide.value.background)
		? 'bg-white-overlay-600'
		: 'bg-gray-100'
	return `${baseClasses} ${bgClass}`
})
</script>
