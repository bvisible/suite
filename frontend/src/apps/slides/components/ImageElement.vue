<template>
	<div>
		<img class="object-cover" :src="imageSrc" :style="imageStyle" />
		<div
			v-if="showReplaceImageButton"
			class="absolute left-0 top-0 size-full overflow-hidden bg-gray-900 opacity-40 transition-opacity duration-500 ease-in-out"
			:style="gradientOverlayStyles"
		>
			<FileUploader
				:fileTypes="allowedImageFileTypes"
				:uploadArgs="{
					doctype: 'Presentation',
					docname: presentationId,
					private: !isPublicPresentation,
				}"
				@success="replaceTemplateImage"
			>
				<template #default="{ openFileSelector }">
					<div :class="replaceButtonClasses" @click="openFileSelector">
						<LucideReplace class="size-5 stroke-[1.5] text-gray-900" />
					</div>
				</template>
			</FileUploader>
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

import { FileUploader } from 'frappe-ui'

import { presentationId, isPublicPresentation } from '@/stores/presentation'
import { allowedImageFileTypes } from '@/utils/constants'
import { activeElement } from '@/stores/element'

const element = defineModel('element', {
	type: Object,
	default: null,
})

const imageSrc = computed(() => {
	if (element.value.src.startsWith('/private')) return element.value.src
	return `/private${element.value.src}`
})

const replaceButtonClasses =
	'absolute inset-[calc(50%-16px)] flex size-8 cursor-pointer items-center justify-center rounded-lg bg-white'

const showReplaceImageButton = computed(() => {
	return (
		element.value.useTemplateDimensions &&
		activeElement.value?.id == element.value.id &&
		element.value.src.includes('placeholder')
	)
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
		transform: `scale(${element.value.invertX || 1}, ${element.value.invertY || 1})`,
		userSelect: 'none',
	}
	if (element.value.useTemplateDimensions) {
		styles.height = `${element.value.height}px`
	}
	return styles
})

const replaceTemplateImage = (file) => {
	const src = isPublicPresentation.value ? file.file_url : file.file_url.replace('/private', '')
	element.value.src = src
	element.value.attachmentName = file.name
}

const gradientOverlayStyles = computed(() => ({
	borderRadius: `${element.value.borderRadius}px`,
}))
</script>
