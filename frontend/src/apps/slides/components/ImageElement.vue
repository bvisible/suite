<template>
	<div>
		<img
			v-if="imageSrc"
			class="object-cover"
			:style="imageStyle"
			:src="getAttachmentUrl(imageSrc)"
		/>
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
					private: true,
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

import { presentationId } from '@/apps/slides/stores/presentation'
import { activeElement } from '@/apps/slides/stores/element'
import { allowedImageFileTypes } from '@/apps/slides/utils/constants'
import { getAttachmentUrl } from '@/apps/slides/utils/mediaUploads'

const props = defineProps({
	mode: {
		type: String,
		default: 'editor',
	},
	transitionStyles: {
		type: Object,
		default: () => ({}),
	},
})

const element = defineModel('element', {
	type: Object,
	default: null,
})

const replaceButtonClasses =
	'absolute inset-[calc(50%-16px)] flex size-8 cursor-pointer items-center justify-center rounded-lg bg-white'

const showReplaceImageButton = computed(() => {
	return (
		props.mode == 'editor' &&
		element.value.useTemplateDimensions &&
		activeElement.value?.id == element.value.id &&
		element.value.src.includes('placeholder')
	)
})

const imageSrc = computed(() => {
	if (props.mode == 'thumbnail' && isGifImage.value && !element.value.poster) {
		return ''
	}
	if (props.mode == 'thumbnail' && element.value.poster) {
		return element.value.poster
	}
	return element.value.src
})

const isGifImage = computed(() => {
	return element.value.src?.split('?')[0].toLowerCase().endsWith('.gif')
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
	return {
		...styles,
		...props.transitionStyles,
	}
})

const replaceTemplateImage = (file) => {
	element.value.src = file.file_url
	element.value.attachmentName = file.name
}

const gradientOverlayStyles = computed(() => ({
	borderRadius: `${element.value.borderRadius}px`,
}))
</script>
