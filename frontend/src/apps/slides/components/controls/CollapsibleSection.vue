<template>
	<div :class="sectionClasses">
		<div class="flex flex-col gap-4 cursor-pointer">
			<div class="flex justify-between items-center" @click="showContent = !showContent">
				<div :class="titleClasses">{{ title }}</div>
				<component
					:is="showContent ? ChevronUp : ChevronDown"
					size="14"
					class="stroke-[1.5] text-gray-500"
				/>
			</div>

			<transition name="slide-fade">
				<div v-if="showContent">
					<div class="flex flex-col gap-4">
						<slot />
					</div>
				</div>
			</transition>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { ChevronDown, ChevronUp } from 'lucide-vue-next'

import { sectionClasses, sectionTitleClasses } from '@/utils/constants'

const props = defineProps({
	title: String,
	titleClasses: {
		type: String,
		default: sectionTitleClasses,
	},
	initialState: {
		type: Boolean,
		default: false,
	},
})

const showContent = ref(props.initialState)
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
