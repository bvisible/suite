<template>
	<div class="flex flex-col gap-4">
		<div class="flex justify-between items-center">
			<div :class="titleClasses">{{ title }}</div>
			<component
				@click="showContent = !showContent"
				:is="showContent ? ChevronUp : ChevronDown"
				size="16"
				class="stroke-[1.5] text-gray-700 cursor-pointer"
			/>
		</div>

		<transition name="slide-fade">
			<div v-if="showContent">
				<slot />
			</div>
		</transition>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

const props = defineProps({
	title: String,
	titleClasses: {
		type: String,
		default: 'text-base text-gray-700',
	},
})

const showContent = ref(false)
</script>

<style>
.slide-fade-enter-active {
	transition: all 0.1s ease-out;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
	transform: translateY(-10px);
	opacity: 0;
}
</style>
