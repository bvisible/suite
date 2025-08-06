<template>
	<Dialog class="pb-0" :options="{ size: '2xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Theme</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto p-2">
				<div
					v-for="(theme, idx) in themeResource.data"
					:key="theme.idx"
					class="flex flex-col gap-3"
				>
					<div
						class="aspect-video cursor-pointer rounded-lg px-2 outline outline-1 outline-offset-2 outline-gray-200 hover:outline-gray-400"
						:style="getThumbnailStyles(theme)"
						@click="$emit('create', theme.name)"
					></div>
					<div class="px-1 text-base text-gray-600">{{ theme.title }}</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, createListResource } from 'frappe-ui'

const emit = defineEmits(['create'])

const themeResource = createListResource({
	doctype: 'Presentation',
	fields: ['name', 'title', 'slug'],
	filters: {
		is_template: '1',
	},
	cache: 'themes',
	auto: true,
	transform: (data) => {
		for (const theme of data) {
			theme.thumbnail = `/assets/slides/frontend/images/layouts/${theme.slug}/thumbnail-3.png`
		}
		return data
	},
})

const getThumbnailStyles = (theme) => {
	return {
		backgroundImage: `url(${theme.thumbnail})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}
</script>
