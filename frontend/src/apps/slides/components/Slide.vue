<template>
	<!-- Slide (Dimensions: 16:9 ratio) -->
	<div
		ref="targetRef"
		class="slide h-[450px] w-[800px] bg-white drop-shadow-lg"
		:class="
			activeElement?.type == 'slide' ? 'cursor-pointer ring-[1.5px] ring-[#808080]/50' : ''
		"
		v-if="slideElements"
		@click="(e) => focusOnElement(e)"
	>
		<component
			v-for="(element, index) in slideElements"
			:key="index"
			:is="TextElement"
			:element="element"
			@click="(e) => focusOnElement(e, element)"
			:class="activeElement == element ? 'cursor-pointer ring-[1.5px] ring-[#808080]/50' : ''"
		/>
	</div>
</template>

<script setup>
import TextElement from '@/components/TextElement.vue'

defineProps({
	slideElements: Array,
})

const activeElement = defineModel('activeElement', {
	type: Object,
	default: null,
})

const focusOnElement = (e, element = null) => {
	e.stopPropagation()

	if (activeElement.value == e.target) return

	if (e.target.classList.contains('textElement')) {
		activeElement.value = element
	} else {
		activeElement.value = {
			type: 'slide',
		}
	}
}
</script>
