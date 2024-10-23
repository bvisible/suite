<template>
	<div
		:style="elementStyle"
		:class="isEqual(activeElement, element) ? 'outline outline-offset-2 outline-blue-400' : ''"
	>
		<img ref="imageElement" class="imageElement" :src="element.src" />
	</div>
</template>

<script setup>
import { ref, useTemplateRef, computed } from 'vue'
import { activeElement } from '@/stores/slide'
import { isEqual } from 'lodash'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const boxShadow = computed(() => {
	return `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`
})

const elementStyle = computed(() => ({
	position: 'fixed',
	width: `${element.value.width}px`,
	height: 'auto',
	left: `${element.value.left}px`,
	top: `${element.value.top}px`,
	opacity: element.value.opacity / 100,
	borderRadius: element.value.borderRadius + 'px',
	borderStyle: element.value.borderStyle || 'none',
	borderColor: element.value.borderColor,
	borderWidth: element.value.borderWidth + 'px',
	boxShadow: boxShadow.value,
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
