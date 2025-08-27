import { FileUploadHandler, toast } from 'frappe-ui'

import { presentationId } from '../stores/presentation'
import { currentSlide } from '../stores/slide'
import { addMediaElement } from '../stores/element'

const fileUploadHandler = new FileUploadHandler()

const performPostUploadActions = (fileDoc, fileType, targetId, resolve) => {
	if (targetId) {
		const targetElement = currentSlide.value.elements.find((el) => el.id == targetId)
		if (targetElement) {
			targetElement.src = fileDoc.file_url
			targetElement.attachmentName = fileDoc.name
		}
		resolve(fileDoc)
		return
	}

	addMediaElement(fileDoc, fileType)
	resolve(fileDoc)
}

const uploadMedia = (file, fileType, targetId) => {
	return new Promise((resolve, reject) => {
		fileUploadHandler
			.upload(file, {
				doctype: 'Presentation',
				docname: presentationId.value,
				private: true,
			})
			.then((fileDoc) => performPostUploadActions(fileDoc, fileType, targetId, resolve))
			.catch((error) => {
				reject(error)
			})
	})
}

const isDataTransferItem = (obj) => {
	return obj && typeof obj === 'object' && 'kind' in obj && 'getAsFile' in obj
}

const isFile = (obj) => {
	return obj instanceof File
}

const getFileObject = (file) => {
	if (isDataTransferItem(file)) {
		return file.getAsFile()
	} else if (isFile(file)) {
		return file
	}
}

const handleFile = (file, index, length, targetId) => {
	file = getFileObject(file)
	if (!file) return

	const fileType = file.type.split('/')[0]
	if (!['image', 'video'].includes(fileType)) return

	const toastProps = {
		loading: `Uploading (${index + 1}/${length}): ${file.name}`,
		success: (data) => `Uploaded: ${file.name}`,
		error: (data) => 'Upload failed. Please try again.',
	}

	toast.promise(uploadMedia(file, fileType, targetId), toastProps)
}

export const handleUploadedMedia = (files, targetId) => {
	if (files.length == 1) {
		return handleFile(files[0], 0, 1, targetId)
	}

	files.forEach((file, index) => {
		handleFile(file, index, files.length)
	})
}
