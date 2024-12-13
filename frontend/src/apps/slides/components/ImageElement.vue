<template>
	<img :src="element.src" :style="imageStyle" @click="setActiveElement(element)" />
</template>

<script setup>
import { computed } from 'vue'
import { setActiveElement } from '@/stores/element'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const imageStyle = computed(() => ({
	opacity: element.value.opacity / 100,
	borderRadius: `${element.value.borderRadius}px`,
	borderStyle: element.value.borderStyle || 'none',
	borderColor: element.value.borderColor,
	borderWidth: `${element.value.borderWidth}px`,
	boxShadow: `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`,
	transform: `scale(${element.value.invertX}, ${element.value.invertY})`,
	userSelect: 'none',
}))
</script>
