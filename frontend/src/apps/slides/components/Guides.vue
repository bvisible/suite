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

const guideStyles = computed(() => {
	return {
		centerY: {
			backgroundColor: '#70b6f080',
			width: '960px',
			height: '1px',
			position: 'fixed',
			top: '50%',
			display: props.visibilityMap?.vertical ? 'block' : 'none',
		},
		centerX: {
			backgroundColor: '#70b6f080',
			height: '540px',
			width: '1px',
			position: 'fixed',
			left: '50%',
			display: props.visibilityMap?.horizontal ? 'block' : 'none',
		},
	}
})
</script>
