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
					class="absolute top-0 h-full rounded border border-black bg-black"
					:style="{
						width: `${((modelValue - rangeStart) / (rangeEnd - rangeStart)) * 100}%`,
					}"
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
import { ref, useTemplateRef, watch } from 'vue'

const props = defineProps({
	label: String,
	rangeStart: Number,
	rangeEnd: Number,
	rangeStep: {
		type: Number,
		default: 1,
	},
	default: {
		type: Number,
		default: 0,
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
