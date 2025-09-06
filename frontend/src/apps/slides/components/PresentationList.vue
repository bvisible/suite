<template>
	<div :class="backgroundClasses">
		<!-- Header -->
		<div class="cursor-default px-32 text-lg font-semibold text-gray-800 lg:px-40">
			Presentations
		</div>

		<div class="px-32 pb-16 pt-8 lg:px-40">
			<div
				v-if="presentations?.length"
				class="grid grid-cols-3 gap-6 lg:grid-cols-4 lg:gap-8"
			>
				<div
					v-for="presentation in presentations"
					:key="presentation.name"
					class="flex flex-col gap-2"
				>
					<!-- Presentation Card -->
					<!-- added bg-white temporarily to support for first slides with no generated thumbnail -->
					<div
						class="aspect-[16/9] cursor-pointer rounded-lg bg-white shadow-xl hover:scale-[1.01]"
						:style="getCardStyles(presentation)"
						@click="$emit('navigate', presentation.name)"
					></div>

					<!-- Presentation Title -->
					<div class="flex items-center justify-between gap-6 px-1">
						<div
							class="cursor-default truncate font-medium text-gray-700 md:text-sm lg:text-base"
						>
							{{ presentation.title }}
						</div>
						<Dropdown
							v-if="presentation"
							:options="getContextMenuOptions(presentation)"
							placement="right"
						>
							<template #default>
								<LucideEllipsis class="size-3.5 cursor-pointer text-gray-600" />
							</template>
						</Dropdown>
					</div>
				</div>
			</div>
			<div v-else class="text-sm text-gray-600">No presentations created yet.</div>
		</div>
	</div>
</template>

<script setup>
import { h } from 'vue'

import { Dropdown } from 'frappe-ui'
import { Eye, Trash, PenLine, Copy, TvMinimalPlay } from 'lucide-vue-next'

import { getAttachmentUrl } from '@/utils/mediaUploads'

const props = defineProps({
	presentations: Object,
})

const emit = defineEmits(['navigate', 'setPreview', 'openDialog'])

const backgroundClasses = 'size-full bg-gray-100 flex flex-col pt-8 overflow-y-auto'
const contextMenuIconClasses = 'stroke-[1.5] !size-3.5'

const getCardStyles = (presentation) => {
	const thumbnailUrl = getAttachmentUrl(presentation.is_public, presentation.thumbnail || '')
	return {
		backgroundImage: `url(${thumbnailUrl})`,
		backgroundSize: 'cover',
		backgroundPosition: 'center',
	}
}

const getContextMenuOptions = (presentation) => {
	return [
		{
			group: 'Actions',
			items: [
				{
					label: 'Rename',
					icon: h(PenLine, { class: contextMenuIconClasses }),
					onClick: () => emit('openDialog', 'Rename', presentation),
				},
				{
					label: 'Duplicate',
					icon: h(Copy, { class: contextMenuIconClasses }),
					onClick: () => emit('openDialog', 'Duplicate', presentation),
				},
				{
					label: 'Delete',
					icon: h(Trash, { class: contextMenuIconClasses }),
					onClick: () => emit('openDialog', 'Delete', presentation),
				},
			],
		},
		{
			group: 'Explore',
			items: [
				{
					label: 'Preview',
					icon: h(Eye, { class: contextMenuIconClasses }),
					onClick: () => emit('setPreview', presentation),
				},
				{
					label: 'Slideshow',
					icon: h(TvMinimalPlay, { class: contextMenuIconClasses }),
					onClick: () => emit('navigate', presentation.name, true),
				},
			],
		},
	]
}
</script>
