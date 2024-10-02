<template>
	<div
		class="fixed"
		:style="{
			width: unref(rect.width) + 10 + 'px',
			left: parseInt(elementStyle.left) - 5 + 'px',
			height: unref(rect.height) + 10 + 'px',
			top: parseInt(elementStyle.top) - 5 + 'px',
			outline: isEqual(activeElement, element) ? '1px solid #70B6F0' : 'none',
		}"
	>
		<img ref="imageElement" class="imageElement" :style="elementStyle" :src="element.src" />
		<Resizer
			v-if="isEqual(activeElement, element)"
			:element="element"
			:isResizing="isResizing"
		/>
	</div>
</template>

<script setup>
import { ref, unref, useTemplateRef, computed } from 'vue'
import Resizer from './Resizer.vue'
import { useElementBounding } from '@vueuse/core'
import { activeElement } from '@/stores/slide'
import { isEqual } from 'lodash'

const isResizing = ref(false)

const el = useTemplateRef('imageElement')

const rect = useElementBounding(el)

const element = defineModel('element', {
	type: Object,
	default: null,
})

const boxShadow = computed(() => {
	return `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`
})

const elementStyle = computed(() => ({
	position: 'fixed',
	width: element.value.width,
	height: 'auto',
	left: element.value.left,
	top: element.value.top,
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
	cursor: element.value.isDragging ? 'move' : 'default',
}))
</script>
