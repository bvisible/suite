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
import { slideBounds } from '@/stores/slide'
import { computed } from 'vue'

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

const rectAttributes = computed(() => {
	if (!slideBounds.left) return {}
	return {
		x: slideBounds.left,
		y: slideBounds.top - 45,
		width: slideBounds.width,
		height: slideBounds.height,
		fill: 'black',
	}
})
</script>
