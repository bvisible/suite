<template>
	<Dialog
		v-model:open="showLayoutDialog"
		class="pb-0"
		size="4xl"
		title="Select a Template Layout"
	>
		<template #default>
			<div class="grid max-h-[32rem] grid-cols-3 gap-6 overflow-y-auto">
				<div
					v-for="layout in layouts"
					:key="layout.idx"
					class="aspect-video cursor-pointer overflow-hidden rounded-lg border border-gray-300 hover:border-gray-400"
					:style="getThumbnailCardStyles(layout.thumbnail)"
					@click="insertSlideWithLayout(layout)"
				>
					<SlidePreview
						v-if="layout.thumbnail == ''"
						:slide="layout"
						:scale="LAYOUT_PREVIEW_SCALE"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { watch, nextTick, computed } from 'vue'
import { Dialog } from 'frappe-ui'

import SlidePreview from '@/components/SlidePreview.vue'
import { presentationTheme, templateList } from '@/stores/presentation'
import { getThumbnailCardStyles } from '@/utils/helpers'

const LAYOUT_PREVIEW_SCALE = 270 / 960

const emit = defineEmits(['insert'])

const layouts = computed(() => {
	const template = templateList.value?.find((t) => t.name === presentationTheme.value)
	return template?.layouts || []
})

const showLayoutDialog = defineModel({
	name: 'showLayoutDialog',
	required: true,
})

const insertSlideWithLayout = (layout) => {
	showLayoutDialog.value = false
	emit('insert', layout)
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
