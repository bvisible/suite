<template>
	<Dialog class="pb-0" :options="{ size: '2xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Theme</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto">
				<div
					v-for="(theme, idx) in themeResource.data"
					:key="theme.idx"
					class="flex flex-col gap-3"
				>
					<div
						class="aspect-video cursor-pointer rounded-lg border border-gray-200 hover:border-gray-300"
						:style="getThumbnailCardStyles(theme.thumbnail)"
						@click="$emit('create', theme.name)"
					></div>
					<div class="px-1 text-base text-gray-600">{{ theme.title }}</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { Dialog, createResource } from 'frappe-ui'

import { getThumbnailCardStyles } from '@/utils/helpers'

const emit = defineEmits(['create'])

const themeResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_themes',
	cache: 'themes',
	auto: true,
})
</script>
