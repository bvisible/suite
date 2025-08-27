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
		let targetId = null
		const target = document.elementFromPoint(e.clientX, e.clientY)
		if (target.tagName == 'IMG') {
			targetId = target.parentElement.parentElement.getAttribute('data-index')
		}
		handleUploadedMedia(e.dataTransfer.files, targetId)
	})
}
</script>
