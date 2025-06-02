<template>
	<button
		class="flex items-center space-x-2 rounded-full border px-2 py-1.5"
		:class="{ 'cursor-pointer hover:border-gray-400': true }"
		@click="blobID && fetchAttachment.submit()"
	>
		<Paperclip class="h-3.5 min-h-3.5 w-3.5 min-w-3.5 text-gray-500" />
		<span class="truncate text-sm">{{ fileName }}</span>
	</button>
</template>

<script setup lang="ts">
import { Paperclip } from 'lucide-vue-next'
import { createResource } from 'frappe-ui'

const { fileName, blobID, type } = defineProps<{
	fileName: string
	blobID?: string
	type?: string
}>()

const fetchAttachment = createResource({
	url: 'mail.api.mail.fetch_attachment',
	makeParams: () => ({ blob_id: blobID }),
	cache: ['attachment', blobID],
	onSuccess: (data: number[]) => {
		const byteArray = new Uint8Array(data)
		const blob = new Blob([byteArray], { type })
		const url = URL.createObjectURL(blob)
		window.open(url, '_blank')
	},
})
</script>
