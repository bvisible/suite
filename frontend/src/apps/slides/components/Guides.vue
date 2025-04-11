<template>
	<div v-for="guide in ['centerX', 'centerY']" :key="guide" :style="guideStyles[guide]"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	visibilityMap: {
		type: Object,
		default: null,
	},
})

const commonStyles = {
	backgroundColor: '#70b6f080',
	position: 'fixed',
}

const getCenterStyles = (axis) => {
	return {
		...commonStyles,
		width: axis === 'horizontal' ? '1px' : '100%',
		height: axis === 'vertical' ? '1px' : '100%',
		left: axis === 'horizontal' ? '50%' : '0',
		top: axis === 'vertical' ? '50%' : '0',
		display: props.visibilityMap?.[axis] ? 'block' : 'none',
	}
}

const guideStyles = computed(() => {
	return {
		centerX: getCenterStyles('horizontal'),
		centerY: getCenterStyles('vertical'),
	}
})
</script>
