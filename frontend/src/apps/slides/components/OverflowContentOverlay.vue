<template>
	<div :style="maskStyles">
		<svg width="100vw" height="100vh">
			<!-- everything that overflows the slideBounds will be covered by an overlay -->
			<defs>
				<mask id="hole-mask" x="0" y="0" width="100%" height="100%">
					<!-- span entire mask area for backdrop -->
					<rect width="100%" height="100%" fill="white" />

					<!-- cutout the section for the slide -->
					<rect v-bind="rectAttributes" />
				</mask>
			</defs>
		</svg>
	</div>
</template>

<script setup>
import { computed, onActivated, onDeactivated, onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
	readonlyMode: {
		type: Boolean,
		default: false,
	},
	transform: {
		type: String,
		default: '',
	},
})

const maskStyles = computed(() => ({
	position: 'absolute',
	top: 0,
	left: 0,
	width: '100vw',
	height: '100vh',
	background: 'rgba(255, 255, 255, 0.6)',
	backdropFilter: 'blur(0.6px)',
	mask: 'url(#hole-mask)',
	webkitMask: 'url(#hole-mask)',
	pointerEvents: 'none',
}))

const windowWidth = ref(0)
const windowHeight = ref(0)

const rectAttributes = computed(() => {
	if (!windowWidth.value) {
		windowWidth.value = window.innerWidth
	}
	if (!windowHeight.value) {
		windowHeight.value = window.innerHeight
	}

	const [a, b, c, d, e, f] = props.transform
		.replace('matrix(', '')
		.replace(')', '')
		.split(',')
		.map((num) => parseFloat(num))

	const factor = props.readonlyMode ? -95.5 : 32

	const tx = (windowWidth.value - 960) / 2 - factor
	const ty = (windowHeight.value - 540) / 2 - 22.5

	const combinedTx = e + tx
	const combinedTy = f + ty

	const combinedMatrix = `matrix(${a},${b},${c},${d},${combinedTx},${combinedTy})`

	return {
		x: 0,
		y: 0,
		width: '960px',
		height: '540px',
		fill: 'black',
		transform: combinedMatrix,
	}
})

const updateWindowSize = () => {
	windowWidth.value = window.innerWidth
	windowHeight.value = window.innerHeight
}

onMounted(() => {
	window.addEventListener('resize', updateWindowSize)
})

onBeforeUnmount(() => {
	window.removeEventListener('resize', updateWindowSize)
})

onActivated(() => {
	window.addEventListener('resize', updateWindowSize)
})

onDeactivated(() => {
	window.removeEventListener('resize', updateWindowSize)
})
</script>
