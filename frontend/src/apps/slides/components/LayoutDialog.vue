<template>
	<Dialog v-model="showLayoutDialog" class="pb-0" :options="{ size: '4xl' }">
		<template #body-title>
			<div ref="titleRef" class="font-semibold">Select a Template Layout</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-3 gap-6 overflow-y-auto">
				<div
					v-for="layout in layouts.data"
					:key="layout.idx"
					class="aspect-video cursor-pointer rounded-lg border hover:border-gray-500"
					:style="getThumbnailStyles(layout)"
					@click="insertSlideWithLayout(layout)"
				></div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { nextTick, ref, useTemplateRef, watch } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

const emit = defineEmits(['insert'])

const titleRef = useTemplateRef('titleRef')

const showLayoutDialog = defineModel({
	name: 'showLayoutDialog',
	required: true,
})

const layouts = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_layouts',
	method: 'GET',
	auto: true,
})

const getThumbnailStyles = (layout) => {
	return {
		backgroundImage: `url(${layout.thumbnail || ''})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}

const insertSlideWithLayout = (layout) => {
	emit('insert', layout.name)
}

watch(
	() => showLayoutDialog.value,
	(visibility) => {
		if (visibility) {
			nextTick(() => {
				document.activeElement?.blur()
			})
		}
	},
)
</script>
