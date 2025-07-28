<template>
	<Dialog class="pb-0" :options="{ size: '2xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Theme</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto">
				<div v-for="(theme, idx) in themes" :key="theme.idx" class="flex flex-col gap-2">
					<div
						class="aspect-video cursor-pointer rounded-lg border hover:border-gray-400"
						:style="getThumbnailStyles(theme)"
					></div>
					<div class="px-1 text-base text-gray-600">{{ theme.name }}</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog } from 'frappe-ui'

const themes = [
	{
		name: 'Default',
		thumbnail: '/assets/slides/frontend/images/layouts/default/thumbnail-3.png',
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
