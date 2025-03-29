<template>
	<div
		class="bg-white w-56 rounded-lg h-10 fixed bottom-10 left-[50%-144px] shadow-2xl flex items-center gap-1 p-1 justify-center"
	>
		<Tooltip
			v-for="option in contentActions"
			:text="option.label"
			:hover-delay="0.7"
			placement="bottom"
		>
			<div
				v-if="option.label == 'Text'"
				class="p-2 rounded hover:bg-gray-100 cursor-pointer"
				@click="addTextElement"
			>
				<component :is="option.icon" size="14" class="stroke-[1.5]" />
			</div>

			<FileUploader
				v-else-if="['Video', 'Image'].includes(option.label)"
				:fileTypes="['video/*', 'image/*']"
				@success="(file) => handleUploadSuccess(file, option.label)"
			>
				<template #default="{ openFileSelector }">
					<div
						class="p-2 rounded hover:bg-gray-100 cursor-pointer"
						@click="openFileSelector"
					>
						<component :is="option.icon" size="14" class="stroke-[1.5]" />
					</div>
				</template>
			</FileUploader>
		</Tooltip>

		<div class="h-6 mx-1 border-l"></div>

		<Tooltip
			v-for="option in slideActions"
			:text="option.label"
			:hover-delay="0.5"
			placement="bottom"
		>
			<div
				class="p-2 rounded hover:bg-gray-100 cursor-pointer"
				@click="option.onClick"
				@mouseenter="emit('setHighlight', true)"
				@mouseleave="emit('setHighlight', false)"
			>
				<component :is="option.icon" size="14" class="stroke-[1.5]" />
			</div>
		</Tooltip>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { toast } from 'vue-sonner'

import { Type, Image, Film, Trash, Copy, SquarePlus } from 'lucide-vue-next'

import { Tooltip, FileUploader } from 'frappe-ui'
import { addTextElement, addMediaElement } from '@/stores/element'

const emit = defineEmits(['insert', 'delete', 'duplicate', 'setHighlight'])

const contentActions = [
	{
		label: 'Text',
		icon: Type,
	},
	{
		label: 'Image',
		icon: Image,
	},
	{
		label: 'Video',
		icon: Film,
	},
]

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

const handleUploadSuccess = (file, type) => {
	type = type.toLowerCase()
	addMediaElement(file, type)
	toast.success('Uploaded: ' + file.file_name)
}

const handleUploadFailure = () => {
	toast.error('Upload failed. Please try again.')
}
</script>
