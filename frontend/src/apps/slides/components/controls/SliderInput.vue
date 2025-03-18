<template>
	<div class="flex flex-col gap-1">
		<div class="text-sm text-gray-600">{{ label }}</div>
		<div class="flex items-center justify-between">
			<div class="relative me-4 h-[1px] w-full">
				<input
					class="slider absolute top-0 h-full"
					type="range"
					:min="rangeStart"
					:max="rangeEnd"
					:step="rangeStep"
					:value="modelValue"
					@input="$emit('update:modelValue', $event.target.value)"
				/>
				<div
					class="absolute top-0 h-full rounded border bg-black border-black"
					:style="highlightStyles"
				></div>
			</div>
			<input
				v-if="showInput"
				type="number"
				class="h-7 w-10 rounded border border-gray-400 px-1 py-0 text-center text-sm focus:border-[1.5px] focus:border-gray-500 focus:ring-0"
				:value="modelValue"
				@change="changeValue"
			/>
		</div>
	</div>
</template>

<script setup>
import { ref, useTemplateRef, computed } from 'vue'

const props = defineProps({
	label: String,
	rangeStart: Number,
	rangeEnd: Number,
	rangeStep: {
		type: Number,
		default: 1,
	},
	showInput: {
		type: Boolean,
		default: true,
	},
	modelValue: {
		type: Number,
		required: true,
	},
})

const emit = defineEmits(['update:modelValue'])

const sliderBar = useTemplateRef('slider')

const changeValue = (e) => {
	const value = parseFloat(e.target.value)
	emit('update:modelValue', Math.max(props.rangeStart, Math.min(props.rangeEnd, value)))
}

const highlightStyles = computed(() => {
	const { rangeStart, rangeEnd, modelValue: val } = props

	let left = 0
	let width = 0

	if (rangeStart < 0) {
		left = Math.abs(rangeStart)
		if (val <= 0) left -= Math.abs(val)
		width = Math.abs(val)
	} else {
		left = 0
		width = val - rangeStart
	}

	return {
		left: `${(left / (rangeEnd - rangeStart)) * 100}%`,
		width: `${(width / (rangeEnd - rangeStart)) * 100}%`,
	}
})
</script>
<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}

.slider {
	-webkit-appearance: none;
	width: 100%;
	height: 2px;
	background: #d3d3d3;
	outline: none;
	-webkit-transition: 0.2s;
	transition: opacity 0.2s;
	border-radius: 10px;
}

.slider:hover {
	opacity: 1;
}

.slider::-webkit-slider-thumb {
	-webkit-appearance: none;
	appearance: none;
	width: 10px;
	height: 10px;
	background: #000000;
	cursor: pointer;
	border-radius: 50%;
}
</style>
