<template>
	<div class="slides-container">
		<div
			v-for="slide in slides"
			:key="slide.id"
			class="slide-page"
			:style="getSlidePageStyles(slide)"
		>
			<SlideElement
				v-for="element in slide?.elements"
				:key="`print-${element.id}`"
				mode="slideshow"
				:element="element"
				:data-index="element.id"
			/>
		</div>
	</div>
</template>

<script setup>
import { defineProps } from 'vue'

import SlideElement from '@/components/SlideElement.vue'

const props = defineProps({
	slides: { type: Array, required: true },
})

const getSlidePageStyles = (slide) => {
	return {
		backgroundColor: slide.background || 'white',
	}
}
</script>

<style>
@media print {
	body > * {
		display: none !important;
	}

	.slides-container,
	.slides-container * {
		display: block !important;
	}

	@page {
		size: 960px 540px;
		margin: 0;
	}
}

.slides-container {
	display: none;
	background: white;
}

.slide-page {
	position: relative;
	width: 960px !important;
	height: 540px !important;
	transform: none !important;
	page-break-after: always;
	overflow: hidden;
}
</style>
