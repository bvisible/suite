<template>
	<Dialog v-model="showLayoutDialog" class="pb-0" :options="{ size: '4xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Template Layout</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-3 gap-6 overflow-y-auto p-2">
				<div
					v-for="layout in layouts.slides"
					:key="layout.idx"
					class="aspect-video cursor-pointer rounded-lg border border-gray-300 hover:border-gray-400"
					:style="getThumbnailStyles(layout)"
					@click="insertSlideWithLayout(layout)"
				></div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { watch, nextTick, computed } from 'vue'
import { Dialog } from 'frappe-ui'

import { getAttachmentUrl } from '@/utils/mediaUploads'

const emit = defineEmits(['insert'])

const props = defineProps({
	theme: String,
	layouts: {
		type: Object,
		required: true,
	},
})

const showLayoutDialog = defineModel({
	name: 'showLayoutDialog',
	required: true,
})

const getThumbnailStyles = (layout) => {
	const thumbnailUrl = getAttachmentUrl(layout.is_public, layout.thumbnail || '')
	return {
		backgroundImage: `url(${thumbnailUrl})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}

const insertSlideWithLayout = (layout) => {
	showLayoutDialog.value = false
	emit('insert', layout.name)
}

watch(
	() => showLayoutDialog.value,
	(visibility) => {
		if (!visibility) return
		nextTick(() => {
			// TODO: fix dialog to not focus on close button
			document.activeElement?.blur()
		})
	},
)
</script>
