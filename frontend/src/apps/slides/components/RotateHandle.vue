<template>
	<div :style="rotateHandleStyles" class="flex items-center justify-center">
		<LucideRotateCw class="stroke-[1.5] text-white" :style="rotateIconStyles" />
	</div>
</template>
<script setup>
import { computed } from 'vue'

import { slideBounds } from '@/stores/slide'

const rotateHandleStyles = computed(() => {
	const size = 20 / slideBounds.scale
	const offsetY = -20 / slideBounds.scale - size / 2
	return {
		position: 'absolute',
		zIndex: 9999,
		backgroundColor: '#70b6f0',
		borderRadius: '50%',
		cursor: 'grab',
		left: `calc(50% - ${size / 2}px)`,
		top: `${offsetY}px`,
		width: `${size}px`,
		height: `${size}px`,
		opacity: 0.8,
	}
})

const rotateIconStyles = computed(() => {
	const iconSize = 12 / slideBounds.scale
	return {
		width: `${iconSize}px`,
		height: `${iconSize}px`,
	}
})
</script>
