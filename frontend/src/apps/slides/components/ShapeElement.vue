<template>
	<svg :style="shapeStyles">
		<defs v-if="hasMarkers || shadow.hasShadow">
			<filter
				v-if="shadow.hasShadow"
				:id="shadowFilterId"
				filterUnits="userSpaceOnUse"
				x="-1000"
				y="-1000"
				width="3000"
				height="3000"
				color-interpolation-filters="sRGB"
			>
				<feDropShadow
					:dx="shadow.offsetX"
					:dy="shadow.offsetY"
					:stdDeviation="shadow.stdDeviation"
					:flood-color="shadow.color"
					:flood-opacity="shadow.opacity"
				/>
			</filter>

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
			:filter="shadow.hasShadow ? `url(#${shadowFilterId})` : null"
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
			:filter="shadow.hasShadow ? `url(#${shadowFilterId})` : null"
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
			:filter="shadow.hasShadow ? `url(#${shadowFilterId})` : null"
		/>
	</svg>
</template>

<script setup>
import { computed } from 'vue'
import { useSVGShadow } from '@/composables/useSVGShadow'

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

const hasMarkers = computed(() => {
	if (!element.value) return false
	if (element.value.shapeType != 'line') return false
	return element.value.markerStart || element.value.markerEnd
})

const markerStartId = computed(() => `line-marker-start-${element.value?.id || ''}`)
const markerEndId = computed(() => `line-marker-end-${element.value?.id || ''}`)

const shadowFilterId = computed(() => `shape-shadow-${element.value?.id || ''}`)
const shadow = useSVGShadow(element)

const shapeStyles = computed(() => {
	const styles = {
		width: '100%',
		height: '100%',
		opacity: (element.value?.opacity || 100) / 100,
		overflow: hasMarkers.value || shadow.value.hasShadow ? 'visible' : '',
	}
	return {
		...styles,
		...props.transitionStyles,
	}
})
</script>
