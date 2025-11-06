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
import { ref, useTemplateRef, nextTick } from 'vue'

import { isPublicPresentation, presentationId } from '@/stores/presentation'
import { handleUploadedMedia } from '@/utils/mediaUploads'
import { currentSlide } from '@/stores/slide'

const emit = defineEmits(['hideOverlay'])

const overlayRef = useTemplateRef('overlay')

const handleDragLeave = (e) => {
	e.preventDefault()
	emit('hideOverlay')
}

const getTargetElement = (e) => {
	const target = document.elementFromPoint(e.clientX, e.clientY).closest('[data-index]')

	if (!target) return null

	const elementId = target.getAttribute('data-index')
	const element = currentSlide.value.elements.find((el) => el.id == elementId)

	if (element && ['image', 'video'].includes(element.type)) {
		return element
	}
}

const handleMediaDrop = async (e) => {
	e.preventDefault()
	emit('hideOverlay')
	nextTick(() => {
		const targetElement = getTargetElement(e)
		handleUploadedMedia(e.dataTransfer.files, targetElement)
	})
}
</script>
