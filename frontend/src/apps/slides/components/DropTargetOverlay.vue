<template>
	<div
		ref="overlay"
		class="absolute left-0 top-0 size-full bg-blue-400 opacity-10"
		@dragleave.prevent="handleDragLeave"
		@dragover.prevent
		@drop="handleMediaDrop"
	></div>
</template>

<script setup>
import { nextTick, ref, useTemplateRef } from 'vue'

import { presentationId } from '@/stores/presentation'
import { handleUploadedMedia } from '@/utils/mediaUploads'
import { currentSlide } from '@/stores/slide'

const emit = defineEmits(['hideOverlay'])

const overlayRef = useTemplateRef('overlay')

const handleDragLeave = (e) => {
	e.preventDefault()
	emit('hideOverlay')
}

const handleMediaDrop = async (e) => {
	e.preventDefault()
	emit('hideOverlay')
	nextTick(() => {
		let targetElement = null
		const target = document.elementFromPoint(e.clientX, e.clientY)
		const closestElement = target.closest('[data-index]')
		if (closestElement) {
			const elementId = closestElement.getAttribute('data-index')
			const element = currentSlide.value.elements.find((el) => el.id == elementId)
			if (element && ['image', 'video'].includes(element.type)) {
				targetElement = element
			}
		}
		handleUploadedMedia(e.dataTransfer.files, targetElement)
	})
}
</script>
