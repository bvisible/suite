<template>
	<div>
		<div :style="shapeStyle"></div>
	</div>
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
	const offsetHeight = isActive.value ? props.elementOffset.height : 0

	let elementHeight = element.value.height
	if (elementHeight) {
		elementHeight = `${elementHeight + offsetHeight}px`
	} else {
		elementHeight = 'auto'
	}

	const styles = {
		width: '100%',
		height: elementHeight,
		opacity: element.value.opacity / 100,
		backgroundColor: element.value.fillColor,
	}
	return {
		...styles,
		...props.transitionStyles,
	}
})
</script>
