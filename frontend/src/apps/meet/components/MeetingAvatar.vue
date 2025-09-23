<template>
	<div class="flex items-center justify-center w-full h-full pointer-events-none">
		<div
			class="relative flex items-center justify-center rounded-full overflow-hidden bg-gradient-to-br from-gray-500 to-gray-600 text-white shadow-inner max-w-full max-h-full"
			:class="sizeClasses"
		>
			<img
				v-if="image"
				:src="image"
				alt="avatar"
				class="w-full h-full object-cover"
				draggable="false"
			/>
			<span v-else class="font-semibold select-none" :class="textClasses">
				{{ label }}
			</span>
		</div>
	</div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
	image: { type: String, default: "" },
	label: { type: String, default: "" },
	tiles: { type: Number, default: 1 }, // number of visible tiles in grid
});

// Dynamic sizing tiers based on total visible tiles (reduced a notch)
// <=4 (1x1,2x2)       : large (slightly reduced)
// 5-9  (up to 3x3)    : medium
// 10-16 (4x4 max)     : small
// >16 (overflow mode) : extra small
const sizeClasses = computed(() => {
	// Reduced sizes: make placeholders smaller for a denser layout
	if (props.tiles <= 4) return "w-28 h-28";
	if (props.tiles <= 9) return "w-20 h-20";
	if (props.tiles <= 16) return "w-16 h-16";
	return "w-12 h-12";
});

const textClasses = computed(() => {
	if (props.tiles <= 9) return "text-3xl tracking-wide";
	if (props.tiles <= 16) return "text-xl";
	return "text-sm";
});
</script>

<style scoped>
@media (prefers-reduced-motion: no-preference) {
	.pulse-soft {
		animation: pulseSoft 5s ease-in-out infinite;
	}
	@keyframes pulseSoft {
		0%,
		100% {
			transform: scale(1);
			filter: brightness(1);
		}
		50% {
			transform: scale(1.03);
			filter: brightness(1.08);
		}
	}
}
</style>
