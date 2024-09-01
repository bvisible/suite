<template>
	<div class="fixed flex h-screen w-screen flex-col bg-gray-50">
		<div class="flex items-center justify-between bg-white p-2 shadow-xl shadow-gray-200">
			<div class="flex items-center gap-2">
				<Logo />
				<div class="font-semibold">Slides</div>
			</div>

			<div class="flex justify-between">
				<Button variant="solid" label="Present" size="sm">
					<template #prefix>
						<SlideshowIcon class="h-4 w-4" />
					</template>
				</Button>
			</div>
		</div>

		<div ref="containerRef" class="-z-10 flex h-full items-center justify-center">
			<!-- slide dimensions: 16:9 ratio -->
			<div ref="targetRef" class="h-[540px] w-[960px] bg-white drop-shadow-lg"></div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

import Logo from '@/icons/Logo.vue'
import SlideshowIcon from '@/icons/SlideshowIcon.vue'

const containerRef = ref(null)
const targetRef = ref(null)

const startZoom = (target, transform, initialTransform) => {
	let rect = target.getBoundingClientRect()
	origin = {
		x: transform.origin.x - rect.x,
		y: transform.origin.y - rect.y,
	}
	let m = getMatrix(transform).multiply(initialTransform)
	target.style.transform = m
}

const updateTransform = (target, transform, initialTransform) => {
	let m = getMatrix(transform).multiply(initialTransform)
	target.style.transform = m
}

const endZoom = (target, transform, initialTransform) => {
	initialTransform = getMatrix(transform).multiply(initialTransform)
	target.style.transform = initialTransform
}

const getMatrix = (transform) => {
	return new DOMMatrix().scale(transform.scale || 1)
}

const setupZooming = (container, target) => {
	let transform,
		wheelTimeout = null

	const handleZoom = (e) => {
		e.preventDefault()

		let initialTransform = new DOMMatrix()

		if (!transform) {
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: 1,
			}
			startZoom(target, transform, initialTransform)
		}

		if (e.ctrlKey) {
			let zoom_factor = e.deltaY <= 0 ? (1 - e.deltaY) / 100 : 1 / (1 + e.deltaY / 100)
			transform = {
				origin: { x: e.clientX, y: e.clientY },
				scale: transform.scale * zoom_factor,
			}
		}

		updateTransform(target, transform, initialTransform)

		if (wheelTimeout) window.clearTimeout(wheelTimeout)
		wheelTimeout = setTimeout(() => {
			endZoom(target, transform, initialTransform)
			transform = null
		}, 100)
	}

	container.addEventListener('wheel', handleZoom, {
		passive: false,
	})
}

onMounted(() => {
	if (!containerRef.value || !targetRef.value) return
	setupZooming(containerRef.value, targetRef.value)
})
</script>
