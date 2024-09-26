<template>
	<!-- Render Image Element -->
	<div
		class="fixed"
		:style="{
			width: elementStyle.width,
			left: elementStyle.left,
			height: unref(rect.height) + 'px',
			top: elementStyle.top,
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

const elementStyle = computed(() => ({
	padding: '2px',
	position: 'fixed',
	width: element.value.width,
	height: 'auto',
	left: element.value.left,
	top: element.value.top,
	opacity: element.value.opacity / 100,
	borderRadius: element.value.borderRadius + 'px',
}))
</script>
