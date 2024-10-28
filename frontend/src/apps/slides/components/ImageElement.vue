<template>
	<img :src="element.src" :style="ImageStyle" />
</template>

<script setup>
import { computed } from 'vue'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const imageStyle = computed(() => ({
	opacity: element.value.opacity / 100,
	borderRadius: element.value.borderRadius + 'px',
	borderStyle: element.value.borderStyle || 'none',
	borderColor: element.value.borderColor,
	borderWidth: element.value.borderWidth + 'px',
	boxShadow: `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`,
	transform:
		element.value.invertX && element.value.invertY
			? 'scale(-1, -1)'
			: element.value.invertX
				? 'scale(-1, 1)'
				: element.value.invertY
					? 'scale(1, -1)'
					: 'scale(1, 1)',
	userSelect: 'none',
}))
</script>
