<template>
	<div
		ref="overlay"
		class="bg-blue-400 opacity-10 z-15 size-full fixed top-0 left-0"
		@dragleave.prevent="handleDragLeave"
		@dragover.prevent
		@drop="handleMediaDrop"
	></div>
</template>

<script setup>
import { ref, useTemplateRef } from 'vue'
import { toast } from 'vue-sonner'

import { FileUploadHandler } from 'frappe-ui'

import { presentationId } from '@/stores/presentation'
import { addMediaElement } from '@/stores/element'

const emit = defineEmits(['hideOverlay'])

const overlayRef = useTemplateRef('overlay')

const handleDragLeave = (e) => {
	e.preventDefault()
	emit('hideOverlay', false)
}

const fileUploadHandler = new FileUploadHandler()

const uploadMedia = (file, fileType) => {
	return new Promise((resolve, reject) => {
		fileUploadHandler
			.upload(file, {
				doctype: 'Presentation',
				docname: presentationId.value,
				private: true,
			})
			.then((fileDoc) => {
				addMediaElement(fileDoc, fileType)
				resolve(fileDoc)
			})
			.catch((error) => {
				reject(error)
			})
	})
}

const uploadFiles = (files) => {
	files.forEach((file, index) => {
		const fileType = file.type.split('/')[0]
		if (!['image', 'video'].includes(fileType)) return

		const toastProps = {
			loading: `Uploading (${index + 1}/${files.length}): ${file.name}`,
			success: (data) => `Uploaded: ${file.name}`,
			error: (data) => 'Upload failed. Please try again.',
		}

		// run after current call stack so toast's expand animation works
		setTimeout(() => toast.promise(uploadMedia(file, fileType), toastProps), 0)
	})
}

const handleMediaDrop = async (e) => {
	e.preventDefault()
	emit('hideOverlay', false)
	const files = e.dataTransfer.files
	uploadFiles(files)
}
</script>
