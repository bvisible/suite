<template>
	<Dialog class="pb-0" :options="{ size: '2xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Theme</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto p-2">
				<div v-for="(theme, idx) in themes" :key="theme.idx" class="flex flex-col gap-2">
					<div
						class="aspect-video cursor-pointer rounded-lg px-2 outline outline-1 outline-offset-2 outline-gray-200 hover:outline-gray-400"
						:style="getThumbnailStyles(theme)"
						@click="$emit('create', theme.name)"
					></div>
					<div class="px-1 text-base text-gray-600">{{ theme.name }}</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog } from 'frappe-ui'

const emit = defineEmits(['create'])

const themes = [
	{
		name: 'Light',
		thumbnail: '/assets/slides/frontend/images/layouts/light/thumbnail-3.png',
	},
	{
		name: 'Dark',
		thumbnail: '/assets/slides/frontend/images/layouts/dark/thumbnail-3.png',
	},
]

const getThumbnailStyles = (theme) => {
	return {
		backgroundImage: `url(${theme.thumbnail})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}
</script>
