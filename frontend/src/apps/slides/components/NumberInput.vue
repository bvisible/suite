<template>
	<div class="flex h-full w-full items-center justify-between rounded border bg-gray-50/80">
		<div v-if="prefix" class="px-2 text-center text-xs text-gray-500">{{ prefix }}</div>
		<input
			type="number"
			class="h-full w-full border-none p-0 text-center text-xs font-semibold text-gray-800 focus:border-none focus:outline-none focus:ring-0"
			:class="{ 'rounded-l': !prefix }"
			:value="parseFloat(parseFloat(modelValue).toFixed(2))"
			@change="changeValue"
		/>
		<div v-if="suffix" class="px-2 text-center text-xs text-gray-500">{{ suffix }}</div>
		<div class="flex h-full w-12 flex-col border-l">
			<button
				class="flex h-1/2 cursor-pointer items-center justify-center rounded-tr border-b bg-white hover:bg-gray-200"
				@click="modelValue + rangeStep <= props.rangeEnd && (modelValue += rangeStep)"
			>
				<FeatherIcon name="chevron-up" class="h-3" :strokeWidth="2" />
			</button>
			<button
				class="flex h-1/2 cursor-pointer items-center justify-center rounded-br bg-white hover:bg-gray-200"
				@click="modelValue - rangeStep >= props.rangeStart && (modelValue -= rangeStep)"
			>
				<FeatherIcon name="chevron-down" class="h-3" :strokeWidth="2" />
			</button>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
const props = defineProps({
	prefix: String,
	suffix: String,
	rangeStart: Number,
	rangeEnd: Number,
	rangeStep: {
		type: Number,
		default: 1,
	},
})

const modelValue = defineModel()

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
