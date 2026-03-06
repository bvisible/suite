<template>
	<Dialog v-model="showThemeDialog" class="pb-0" :options="{ size: '2xl' }">
		<template #body-title>
			<div class="font-semibold">{{ dialogTitle }}</div>
		</template>
		<template #body-content>
			<div class="mb-6 text-base text-gray-600">{{ dialogDescription }}</div>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto">
				<div
					v-for="(theme, idx) in themeResource.data"
					:key="theme.idx"
					class="flex flex-col gap-3"
				>
					<div
						class="m-1 aspect-video cursor-pointer rounded-lg border border-gray-200 hover:border-gray-300"
						:class="getThemeThumbnailClasses(theme.name)"
						:style="getThumbnailCardStyles(theme.thumbnail)"
						@click="performAction(theme.name)"
					></div>
					<div class="flex">
						<LucideCheck
							v-if="props.update && theme.name == props.currentTheme"
							class="size-4 stroke-[1.5] text-gray-800"
						/>
						<div class="px-2 text-base text-gray-600">{{ theme.title }}</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { watch, nextTick, onMounted, computed } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

import { getThumbnailCardStyles } from '@/utils/helpers'

const props = defineProps({
	update: {
		type: Boolean,
		default: false,
	},
	currentTheme: String,
})

const showThemeDialog = defineModel({
	name: 'showThemeDialog',
	required: true,
})

const emit = defineEmits(['create'])

const dialogTitle = computed(() => (props.update ? 'Change Theme' : 'New Presentation Theme'))
const dialogDescription = computed(() =>
	props.update
		? 'Update the theme for this presentation. All newly added slides will use this theme.'
		: 'Select a theme for your new presentation. You can change this theme later.',
)

const themeResource = createResource({
	url: 'slides.slides.doctype.presentation.presentation.get_themes',
	cache: 'themes',
	auto: true,
})

const performAction = (theme) => {
	if (props.update) {
		emit('update', theme)
	} else {
		emit('create', theme)
	}
}

watch(
	() => showThemeDialog.value,
	(visibility) => {
		if (!visibility) return
		nextTick(() => {
			document.activeElement?.blur()
		})
	},
)

const getThemeThumbnailClasses = (theme) => {
	return props.update && theme == props.currentTheme ? 'ring-2 ring-offset-2 ring-gray-400' : ''
}
</script>
