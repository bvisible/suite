<template>
	<div class="text-2xs uppercase text-gray-600">{{ label }}</div>
	<div class="flex items-center justify-between">
		<div class="relative my-4 me-6 h-[1.5px] w-full">
			<div ref="sliderBar" class="absolute top-0 h-full w-full rounded bg-gray-300"></div>
			<div
				class="absolute top-0 h-full rounded bg-gray-900"
				:style="{ width: modelValue + '%' }"
			></div>
			<div
				class="absolute -top-[5px] h-3 w-3 cursor-pointer rounded-md border bg-gray-900"
				:style="{ left: modelValue + '%' }"
				@mousedown="handleDragStart"
			></div>
		</div>
		<input
			type="number"
			class="h-7 w-10 rounded border border-gray-400 px-2 py-0 text-center text-sm focus:border-[1.5px] focus:border-gray-500 focus:ring-0"
			:value="modelValue"
			@change="changeValue"
		/>
	</div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
	label: String,
	rangeStart: Number,
	rangeEnd: Number,
})

const modelValue = defineModel()

const sliderBar = ref(null)

const handleDragStart = (e) => {
	e.preventDefault()
	window.addEventListener('mousemove', handleDrag)
	window.addEventListener('mouseup', handleDragEnd)
}

const handleDrag = (e) => {
	e.preventDefault()
	let rect = sliderBar.value.getBoundingClientRect()

	if (e.clientX < rect.left) {
		modelValue.value = props.rangeStart
		return
	} else if (e.clientX > rect.right) {
		modelValue.value = props.rangeEnd
		return
	}

	let currentValue = Math.round(((e.clientX - rect.left) / sliderBar.value.offsetWidth) * 100)
	modelValue.value = Math.min(Math.max(currentValue, props.rangeStart), props.rangeEnd)
}

const handleDragEnd = (e) => {
	e.preventDefault()
	window.removeEventListener('mousemove', handleDrag)
	window.removeEventListener('mouseup', handleDragEnd)
}

const changeValue = (e) => {
	let value = parseFloat(e.target.value)
	if (value < props.rangeStart) {
		modelValue.value = props.rangeStart
	} else if (value > props.rangeEnd) {
		modelValue.value = props.rangeEnd
	} else {
		modelValue.value = value
	}
}
</script>
<style scoped>
input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
	-webkit-appearance: none;
	margin: 0;
}
</style>
