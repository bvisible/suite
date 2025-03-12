<template>
	<img :src="element.src" :style="imageStyle" @click="selectImage" />
</template>

<script setup>
import { computed, useAttrs } from 'vue'

import { setActiveElements } from '@/stores/element'
import { inSlideShow } from '@/stores/presentation'

const attrs = useAttrs()

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

const selectImage = (e) => {
	if (inSlideShow.value) return
	setActiveElements([attrs['data-index']])
}
</script>
