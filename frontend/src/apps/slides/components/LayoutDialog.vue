<template>
	<Dialog v-model="showLayoutDialog" class="pb-0" :options="{ size: '4xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Template Layout</div>
		</template>
		<template #body-content>
			<div class="grid max-h-[32rem] grid-cols-3 gap-6 overflow-y-auto p-2">
				<div
					v-for="layout in layouts"
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
import { Dialog, createDocumentResource } from 'frappe-ui'

const emit = defineEmits(['insert'])

const props = defineProps({
	theme: String,
})

const showLayoutDialog = defineModel({
	name: 'showLayoutDialog',
	required: true,
})

const layouts = computed(() => {
	return props.theme == 'Dark' ? layoutResource.doc.slides_dark : layoutResource.doc.slides
})

const layoutResource = createDocumentResource({
	doctype: 'Slide Layouts',
	name: 'Slide Layouts',
	cache: 'layouts',
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
