import { FileUploadHandler } from 'frappe-ui'
import { toast } from 'vue-sonner'

import { presentationId } from '../stores/presentation'
import { addMediaElement } from '../stores/element'

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

		// run after current call stack so toast's expand animation works
		setTimeout(() => toast.promise(uploadMedia(file, fileType), toastProps), 0)
	})
}
