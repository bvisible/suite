<template>
	<svg :style="shapeStyle">
		<defs v-if="element.shapeType == 'line' && (element.markerStart || element.markerEnd)">
			<marker
				v-if="element.markerStart"
				:id="markerStartId"
				viewBox="0 0 10 10"
				markerWidth="6"
				markerHeight="6"
				refX="2"
				refY="5"
				orient="auto"
			>
				<path d="M10,0 L0,5 L10,10 Z" :fill="element.strokeColor" stroke="none" />
			</marker>
			<marker
				v-if="element.markerEnd"
				:id="markerEndId"
				viewBox="0 0 10 10"
				markerWidth="6"
				markerHeight="6"
				refX="8"
				refY="5"
				orient="auto"
			>
				<path d="M0,0 L10,5 L0,10 Z" :fill="element.strokeColor" stroke="none" />
			</marker>
		</defs>

		<rect
			v-if="element.shapeType == 'rectangle'"
			:x="element.strokeWidth / 2"
			:y="element.strokeWidth / 2"
			:width="`calc(100% - ${element.strokeWidth}px)`"
			:height="`calc(100% - ${element.strokeWidth}px)`"
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

		<line
			v-else-if="element.shapeType == 'line'"
			:x1="0"
			:x2="'100%'"
			:y1="element.strokeWidth / 2"
			:y2="element.strokeWidth / 2"
			:stroke="`${element.strokeColor}`"
			:stroke-width="`${element.strokeWidth}px`"
			:marker-start="element.markerStart ? `url(#${markerStartId})` : null"
			:marker-end="element.markerEnd ? `url(#${markerEndId})` : null"
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

const markerStartId = computed(() => `line-marker-start-${element.value.id}`)
const markerEndId = computed(() => `line-marker-end-${element.value.id}`)

const shapeStyle = computed(() => {
	const styles = {
		width: '100%',
		height: '100%',
		opacity: element.value.opacity / 100,
		overflow: element.value.shapeType == 'line' ? 'visible' : '',
	}
	return {
		...styles,
		...props.transitionStyles,
	}
})
</script>
