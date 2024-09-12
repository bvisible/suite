<template>
	<div class="textElement" :style="elementStyle">
		{{ element.content }}
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
	element: Object,
})

const elementStyle = computed(() => {
	let styles = props.element.styles
	return {
		position: 'absolute',
		top: props.element.y,
		left: props.element.x,
		fontFamily: styles.fontFamily,
		fontSize: styles.fontSize + 'px',
		fontWeight: styles.fontWeight,
		fontStyle: styles.fontStyle,
		textDecoration: styles.textDecoration,
		textTransform: styles.textTransform,
	}
})
</script>
