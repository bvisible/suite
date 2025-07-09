<template>
	<Dialog v-model="showLayoutDialog" class="pb-0" :options="{ size: '2xl' }">
		<template #body-title>
			<div class="font-semibold">Select a Layout</div>
		</template>
		<template #body-content>
			<div class="grid grid-cols-3 gap-4">
				<div
					v-for="layout in layouts.data"
					:key="layout.idx"
					class="aspect-video cursor-pointer rounded-lg border"
					:class="{
						'border-gray-300': currentLayout !== layout.name,
						'border-gray-500': currentLayout === layout.name,
					}"
					:style="getThumbnailStyles(layout)"
					@click="setCurrentLayout(layout)"
				></div>
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				label="Add Slide"
				@click="insertSlideWithLayout"
			/>
		</template>
	</Dialog>
</template>

<script setup>
import { ref } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

const emit = defineEmits(['insert'])

const showLayoutDialog = defineModel({
	name: 'showLayoutDialog',
	required: true,
})

const currentLayout = ref(null)

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

const setCurrentLayout = (layout) => {
	currentLayout.value = layout.name
}

const insertSlideWithLayout = () => {
	emit('insert', currentLayout.value)
	currentLayout.value = null
}
</script>
