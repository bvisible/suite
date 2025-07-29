<template>
	<FileUploader
		:fileTypes="ALLOWED_IMAGE_FILETYPES"
		:uploadArgs="{ doctype: 'Presentation', docname: presentationId, private: true }"
		@success="handleImageReplace"
	>
		<template #default="{ openFileSelector }">
			<img
				class="object-cover"
				:src="element.src"
				:style="imageStyle"
				@dblclick="openFileSelector"
			/>
		</template>
	</FileUploader>
</template>

<script setup>
import { computed } from 'vue'

import { FileUploader } from 'frappe-ui'

import { presentationId } from '@/stores/presentation'

const ALLOWED_IMAGE_FILETYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']

const element = defineModel('element', {
	type: Object,
	default: null,
})

const imageStyle = computed(() => {
	const styles = {
		width: '100%',
		opacity: element.value.opacity / 100,
		borderRadius: `${element.value.borderRadius}px`,
		borderStyle: element.value.borderStyle || 'none',
		borderColor: element.value.borderColor,
		borderWidth: `${element.value.borderWidth}px`,
		boxShadow: `${element.value.shadowOffsetX}px ${element.value.shadowOffsetY}px ${element.value.shadowSpread}px ${element.value.shadowColor}`,
		transform: `scale(${element.value.invertX}, ${element.value.invertY})`,
		userSelect: 'none',
	}
	if (element.value.useTemplateDimensions) {
		styles.height = `${element.value.height}px`
	}
	return styles
})

const handleImageReplace = (file) => {
	element.value.src = file.file_url
	element.value.attachmentName = file.name
}
</script>
