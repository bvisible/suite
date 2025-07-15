<template>
	<button
		class="flex items-center space-x-2 rounded-full border px-2 py-1.5"
		:class="{ 'cursor-pointer hover:border-gray-400': blobID }"
		@click="openAttachment"
	>
		<Loader
			v-if="isLoading"
			class="h-3.5 min-h-3.5 w-3.5 min-w-3.5 animate-spin text-gray-500"
		/>
		<Paperclip v-else class="h-3.5 min-h-3.5 w-3.5 min-w-3.5 text-gray-500" />
		<span class="truncate text-sm">{{ fileName }}</span>
	</button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Loader, Paperclip } from 'lucide-vue-next'
import { createResource } from 'frappe-ui'

const { fileName, blobID, type } = defineProps<{
	fileName: string
	blobID?: string
	type?: string
}>()

const isLoading = ref(false)

const openAttachment = async () => {
	if (!blobID) return
	isLoading.value = true
	await fetchAttachment.submit()
	isLoading.value = false
}

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
	onError: () => (isLoading.value = false),
})
</script>
