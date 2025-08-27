import { FileUploadHandler, toast } from 'frappe-ui'

import { presentationId } from '../stores/presentation'
import { currentSlide } from '../stores/slide'
import { addMediaElement, updateVideoPoster } from '../stores/element'

const fileUploadHandler = new FileUploadHandler()

const performPostUploadActions = (fileDoc, fileType, targetElement, resolve) => {
	if (targetElement) {
		targetElement.src = fileDoc.file_url
		targetElement.attachmentName = fileDoc.name
		if (fileType == 'video') {
			updateVideoPoster(targetElement, fileDoc.file_url)
		}
		resolve(fileDoc)
		return
	}

	addMediaElement(fileDoc, fileType)
	resolve(fileDoc)
}

const uploadMedia = (file, fileType, targetElement) => {
	return new Promise((resolve, reject) => {
		fileUploadHandler
			.upload(file, {
				doctype: 'Presentation',
				docname: presentationId.value,
				private: true,
			})
			.then((fileDoc) => performPostUploadActions(fileDoc, fileType, targetElement, resolve))
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

const handleFile = (file, index, length, targetElement) => {
	file = getFileObject(file)
	if (!file) return

	const fileType = file.type.split('/')[0]
	if (!['image', 'video'].includes(fileType)) return

	const toastProps = {
		loading: `Uploading (${index + 1}/${length}): ${file.name}`,
		success: (data) => `Uploaded: ${file.name}`,
		error: (data) => 'Upload failed. Please try again.',
	}

	toast.promise(uploadMedia(file, fileType, targetElement), toastProps)
}

export const handleUploadedMedia = (files, targetElement) => {
	if (files.length == 1) {
		return handleFile(files[0], 0, 1, targetElement)
	}

	files.forEach((file, index) => {
		handleFile(file, index, files.length)
	})
}
