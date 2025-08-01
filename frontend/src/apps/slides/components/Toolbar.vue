<template>
	<div
		class="fixed bottom-10 left-[calc(50%-128px)] flex h-10 w-48 items-center justify-center gap-1 rounded-lg bg-white p-1 shadow-xl"
	>
		<Tooltip text="Text" :hover-delay="0.7" placement="bottom">
			<div class="cursor-pointer rounded p-2 hover:bg-gray-100" @click="addTextElement(null)">
				<Type size="16" class="stroke-[1.5]" />
			</div>
		</Tooltip>

		<Tooltip text="Media" :hover-delay="0.7" placement="bottom">
			<FileUploader
				:fileTypes="ALLOWED_IMAGE_FILETYPES.concat(['video/*'])"
				:uploadArgs="{ doctype: 'Presentation', docname: presentationId, private: true }"
				@success="(file) => handleUploadSuccess(file)"
			>
				<template #default="{ openFileSelector }">
					<div
						class="cursor-pointer rounded p-2 hover:bg-gray-100"
						@click="openFileSelector"
					>
						<ImagePlus size="16" class="stroke-[1.5]" />
					</div>
				</template>
			</FileUploader>
		</Tooltip>

		<div class="h-6 border-l"></div>

		<Tooltip
			v-for="option in slideActions"
			:text="option.label"
			:hover-delay="0.5"
			placement="bottom"
		>
			<div
				class="cursor-pointer rounded p-2 hover:bg-gray-100"
				@click="option.onClick"
				@mouseenter="emit('setHighlight', true)"
				@mouseleave="emit('setHighlight', false)"
			>
				<component :is="option.icon" size="16" class="stroke-[1.5]" />
			</div>
		</Tooltip>
	</div>
</template>

<script setup>
import { ref } from 'vue'

import { Type, ImagePlus, Trash, Copy, SquarePlus } from 'lucide-vue-next'

import { Tooltip, FileUploader, toast } from 'frappe-ui'
import { presentationId } from '@/stores/presentation'
import { addTextElement, addMediaElement } from '@/stores/element'

const ALLOWED_IMAGE_FILETYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']

const emit = defineEmits(['insert', 'delete', 'duplicate', 'setHighlight'])

const slideActions = [
	{
		label: 'Insert Slide',
		icon: SquarePlus,
		onClick: () => {
			emit('insert')
		},
	},
	{
		label: 'Duplicate Slide',
		icon: Copy,
		onClick: (e) => {
			emit('duplicate', e)
		},
	},
	{
		label: 'Delete Slide',
		icon: Trash,
		onClick: () => {
			emit('delete')
		},
	},
]

const handleUploadSuccess = (file) => {
	const imageTypes = ALLOWED_IMAGE_FILETYPES.map((type) => type.split('/')[1].toUpperCase())
	const fileType = imageTypes.includes(file.file_type) ? 'image' : 'video'

	addMediaElement(file, fileType)

	toast.success('Uploaded: ' + file.file_name)
}

const handleUploadFailure = () => {
	toast.error('Upload failed. Please try again.')
}
</script>
