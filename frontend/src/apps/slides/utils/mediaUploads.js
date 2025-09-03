import { FileUploadHandler, toast } from 'frappe-ui'

import { presentationId } from '../stores/presentation'
import { currentSlide } from '../stores/slide'
import { addMediaElement, replaceMediaElement } from '../stores/element'

const fileUploadHandler = new FileUploadHandler()

const performPostUploadActions = (fileDoc, fileType, targetElement, resolve) => {
	if (targetElement) {
		replaceMediaElement(targetElement, fileDoc, fileType)
		resolve(fileDoc)
		return
	}

	addMediaElement(fileDoc, fileType)
	resolve(fileDoc)
}

const uploadMedia = (file, fileType, targetElement, isPrivate) => {
	return new Promise((resolve, reject) => {
		fileUploadHandler
			.upload(file, {
				doctype: 'Presentation',
				docname: presentationId.value,
				private: isPrivate,
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

const handleFile = (file, isPrivate, toastProps, targetElement) => {
	file = getFileObject(file)
	if (!file) return

	const fileType = file.type.split('/')[0]
	if (!['image', 'video'].includes(fileType)) return

	if (targetElement && targetElement.type != fileType) targetElement = null

	toast.promise(uploadMedia(file, fileType, targetElement, isPrivate), toastProps)
}

const getToastProps = (file, index, length) => {
	return {
		loading: `Uploading (${index + 1}/${length}): ${file.name}`,
		success: (data) => `Uploaded: ${file.name}`,
		error: (data) => 'Upload failed. Please try again.',
	}
}

export const handleUploadedMedia = (files, isPrivate, targetElement) => {
	let toastProps = {}

	if (files.length == 1) {
		toastProps = getToastProps(files[0], 0, 1)
		return handleFile(files[0], isPrivate, toastProps, targetElement)
	}

	files.forEach((file, index) => {
		toastProps = getToastProps(file, index, files.length)
		handleFile(file, isPrivate, toastProps)
	})
}
