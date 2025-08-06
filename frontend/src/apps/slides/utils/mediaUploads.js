import { FileUploadHandler, toast } from 'frappe-ui'

import { presentationId } from '../stores/presentation'
import { slide } from '../stores/slide'
import { addMediaElement } from '../stores/element'

const fileUploadHandler = new FileUploadHandler()

const performPostUploadActions = (fileDoc, fileType, resolve) => {
	for (const element of slide.value.elements) {
		if (!element.useTemplateDimensions) continue

		element.src = fileDoc.file_url
		element.attachmentName = fileDoc.name

		resolve(fileDoc)
		return
	}

	addMediaElement(fileDoc, fileType)
	resolve(fileDoc)
}

const uploadMedia = (file, fileType) => {
	return new Promise((resolve, reject) => {
		fileUploadHandler
			.upload(file, {
				doctype: 'Presentation',
				docname: presentationId.value,
				private: true,
			})
			.then((fileDoc) => performPostUploadActions(fileDoc, fileType, resolve))
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

export const handleUploadedMedia = (files) => {
	files.forEach((file, index) => {
		file = getFileObject(file)
		if (!file) return

		const fileType = file.type.split('/')[0]
		if (!['image', 'video'].includes(fileType)) return

		const toastProps = {
			loading: `Uploading (${index + 1}/${files.length}): ${file.name}`,
			success: (data) => `Uploaded: ${file.name}`,
			error: (data) => 'Upload failed. Please try again.',
		}

		toast.promise(uploadMedia(file, fileType), toastProps)
	})
}
