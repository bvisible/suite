<template>
	<div
		ref="overlay"
		class="z-15 fixed left-0 top-0 size-full bg-blue-400 opacity-10"
		@dragleave.prevent="handleDragLeave"
		@dragover.prevent
		@drop="handleMediaDrop"
	></div>
</template>

<script setup>
import { ref, useTemplateRef } from 'vue'

import { presentationId } from '@/stores/presentation'
import { addMediaElement } from '@/stores/element'
import { handleUploadedMedia } from '@/utils/mediaUploads'

const emit = defineEmits(['hideOverlay'])

const overlayRef = useTemplateRef('overlay')

const handleDragLeave = (e) => {
	e.preventDefault()
	emit('hideOverlay', false)
}

const handleMediaDrop = async (e) => {
	e.preventDefault()
	emit('hideOverlay', false)
	handleUploadedMedia(e.dataTransfer.files)
}
</script>
