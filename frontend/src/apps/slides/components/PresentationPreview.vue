<template>
	<div
		class="fixed left-0 w-full h-full transition-all duration-300 ease-in-out flex items-center"
		:class="presentation ? 'top-0' : 'top-[100%]'"
		@click="hidePreview()"
	>
		<div class="z-20 w-[70%] absolute left-[calc(50%-31%)] flex justify-between" @click.stop>
			<div class="w-[88%] flex flex-col gap-8">
				<!-- Preview -->
				<router-link
					v-if="presentation"
					:to="{
						name: 'PresentationEditor',
						params: { presentationId: presentation?.name },
					}"
					class="aspect-video bg-white cursor-pointer rounded-2xl shadow-2xl"
					:style="previewStyles"
				></router-link>

				<!-- Details -->
				<div class="flex flex-col gap-2 lg:text-base text-sm cursor-default px-2">
					<div
						v-for="(row, index) in previewDetails"
						:key="index"
						class="flex items-center justify-between"
					>
						<div
							v-for="(detailValue, detailLabel) in row"
							:key="detailLabel"
							class="flex items-center gap-2"
						>
							<div class="font-semibold text-gray-700">{{ detailLabel }}</div>
							<div class="font-semibold text-gray-600">{{ detailValue }}</div>
						</div>
					</div>
				</div>
			</div>

			<!-- Actions -->
			<div class="w-[8%] flex flex-col gap-3 pt-[30%]">
				<Tooltip
					v-for="action in presentationActions"
					:text="action.label"
					:hover-delay="0.3"
					placement="right"
				>
					<div
						class="w-8 h-8 flex items-center justify-center rounded cursor-pointer"
						:class="action.label === 'Present' ? 'bg-gray-900' : 'bg-gray-200'"
						@click="action.onClick"
					>
						<component
							:is="action.icon"
							size="16"
							class="stroke-[1.5]"
							:class="{
								'text-white': action.label === 'Present',
							}"
						/>
					</div>
				</Tooltip>
			</div>
		</div>

		<div class="z-10 bg-white h-[53%] w-full absolute bottom-0 left-0" @click.stop></div>
	</div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, onMounted } from 'vue'

import { Tooltip, createResource } from 'frappe-ui'

import { Presentation, Copy, PenLine, Trash } from 'lucide-vue-next'

import dayjs from '@/utils/dayjs'

const props = defineProps({
	presentation: Object,
	required: true,
})

const emit = defineEmits(['setPreview', 'openDialog', 'navigate'])

let interval = null

const previewSlide = ref(0)

const slideThumbnails = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_slide_thumbnails',
	method: 'GET',
	makeParams: () => ({
		presentation: props.presentation.name,
	}),
})

const previewStyles = computed(() => {
	const thumbnail = slideThumbnails.data?.[previewSlide.value] || props.presentation.thumbnail
	return {
		backgroundImage: `url(${thumbnail})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
})

const previewDetails = computed(() => {
	if (!props.presentation) return {}

	const { title, creation, modified } = props.presentation
	return [
		{
			Title: title,
			Modified: dayjs(modified).fromNow(),
		},
		{
			'Total Slides': slideThumbnails.data?.length,
			Created: dayjs(creation).fromNow(),
		},
	]
})

const presentationActions = [
	{
		icon: Presentation,
		label: 'Present',
		onClick: (e) => emit('navigate', props.presentation.name, true),
	},
	{
		icon: PenLine,
		label: 'Edit',
		onClick: (e) => emit('navigate', props.presentation.name),
	},
	{
		icon: Copy,
		label: 'Duplicate',
		onClick: (e) => emit('openDialog', 'Duplicate'),
	},
	{
		icon: Trash,
		label: 'Delete',
		onClick: (e) => emit('openDialog', 'Delete'),
	},
]

const updateCurrentThumbnail = () => {
	// cycle through the thumbnails for preview
	previewSlide.value = (previewSlide.value + 1) % slideThumbnails.data.length
}

const initPreview = async () => {
	await slideThumbnails.fetch()
	interval = setInterval(updateCurrentThumbnail, 2000)
}

const clearPreview = () => {
	previewSlide.value = 0
	clearInterval(interval)
	interval = null
}

const hidePreview = () => {
	emit('setPreview', null)
	clearPreview()
}

onMounted(() => initPreview())

onBeforeUnmount(() => clearPreview())
</script>
