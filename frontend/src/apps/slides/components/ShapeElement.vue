<template>
	<svg :style="shapeStyle">
		<rect
			v-if="element.shapeType == 'rectangle'"
			x="0"
			y="0"
			:width="'100%'"
			:height="'100%'"
			:fill="element.fillColor"
			:stroke="element.strokeColor"
			:stroke-width="`${element.strokeWidth}px`"
			:rx="element.borderRadius"
			:ry="element.borderRadius"
		/>

		<ellipse
			v-else-if="element.shapeType == 'circle'"
			cx="50%"
			cy="50%"
			:rx="'calc(50% - ' + element.strokeWidth / 2 + 'px)'"
			:ry="'calc(50% - ' + element.strokeWidth / 2 + 'px)'"
			:fill="element.fillColor"
			:stroke="element.strokeColor"
			:stroke-width="`${element.strokeWidth}px`"
		/>
	</svg>
</template>

<script setup>
import { computed } from 'vue'
import { activeElementIds } from '@/stores/element'

const props = defineProps({
	transitionStyles: {
		type: Object,
		default: () => ({}),
	},
	elementOffset: {
		type: Object,
		default: () => ({ left: 0, top: 0 }),
	},
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const isActive = computed(() => {
	return activeElementIds.value.includes(element.value.id)
})

const shapeStyle = computed(() => {
	const styles = {
		width: '100%',
		height: '100%',
		opacity: element.value.opacity / 100,
	}
	return {
		...styles,
		...props.transitionStyles,
	}
})
</script>
