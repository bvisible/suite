<template>
	<div :style="styles" class="backdrop-blur-sm opacity-85 text-black" :class="indicatorClasses">
		<div v-if="type === 'text'">{{ Math.round(dimensions.width) }}</div>
		<template v-else>
			<div>{{ Math.round(dimensions.width) }} × {{ Math.round(dimensions.height) }}</div>
		</template>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { slide } from '@/stores/slide'
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
	zIndex: 100,
	...props.indicatorStyles,
}))

const indicatorClasses = computed(() => {
	const isDark = isBackgroundColorDark(slide.value.background)
	return [isDark ? 'bg-white-overlay-600' : 'bg-gray-100']
})
</script>
