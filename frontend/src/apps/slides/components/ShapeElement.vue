<template>
	<div>
		<div :style="shapeStyle"></div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
	transitionStyles: {
		type: Object,
		default: () => ({}),
	},
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const shapeStyle = computed(() => {
	const styles = {
		width: '100%',
		height: element.value.height + 'px',
		opacity: element.value.opacity / 100,
		backgroundColor: element.value.fillColor,
	}
	return {
		...styles,
		...props.transitionStyles,
	}
})
</script>
