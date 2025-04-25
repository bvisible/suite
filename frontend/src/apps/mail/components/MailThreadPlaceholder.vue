<template>
	<div class="animate-pulse space-y-4 px-2.5 py-3 sm:px-5 sm:py-6">
		<div v-for="i in Math.ceil(Math.random() * 4)" :key="i" class="rounded-md border p-3">
			<div class="flex space-x-3 border-b pb-2">
				<span class="bg-surface-gray-3 h-6.5 w-6.5 rounded-full" />
				<div class="flex flex-1 justify-between">
					<div class="flex flex-col space-y-1">
						<span class="bg-surface-gray-3 h-4 w-40" />
						<span class="bg-surface-gray-3 h-3 w-48" />
					</div>
					<div class="flex items-center space-x-2">
						<span class="bg-surface-gray-3 h-3 w-12 sm:w-20" />
						<span class="bg-surface-gray-3 h-3 w-3 rounded" />
						<span class="bg-surface-gray-3 h-3 w-3 rounded" />
					</div>
				</div>
			</div>
			<div class="mt-3 space-y-2">
				<div
					v-for="j in Math.ceil(Math.random() * 5)"
					:key="j"
					class="bg-surface-gray-3 h-2"
					:style="{ width: generatePLaceholderWidth() }"
				/>
			</div>
			<div v-if="Math.random() > 0.8" class="mt-5 flex flex-wrap space-x-2">
				<div
					v-for="k in Math.ceil(Math.random() * 3)"
					:key="k"
					class="bg-surface-gray-3 mb-2 h-6 w-24 rounded"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useScreenSize } from '@/utils/composables'

const { size } = useScreenSize()

const generatePLaceholderWidth = () => {
	const width = size.width
	const max = width < 640 ? width - 50 : width / 2
	const min = width < 640 ? width / 2 : width / 3
	return `${Math.floor(Math.random() * (max - min + 1) + min)}px`
}
</script>
