<template>
	<a
		class="flex items-center space-x-1.5 rounded-full border px-2 py-1.5"
		:class="{ 'cursor-pointer hover:bg-gray-100': fileUrl }"
		:href="fileUrl"
		target="_blank"
	>
		<Paperclip class="h-3.5 min-h-3.5 w-3.5 min-w-3.5 text-gray-500" />
		<span class="truncate text-xs">{{ fileName }}</span>
	</a>
</template>

<script setup lang="ts">
import { Paperclip } from 'lucide-vue-next'

defineProps<{ fileName: string; fileUrl?: string }>()
</script>
