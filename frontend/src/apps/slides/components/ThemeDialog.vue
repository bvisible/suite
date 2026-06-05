<template>
	<Dialog
		v-model:open="showThemeDialog"
		class="pb-0"
		size="2xl"
		:title="dialogTitle"
		:dismissible="update"
	>
		<template #default>
			<div class="mb-6 select-none text-base text-gray-600">{{ dialogDescription }}</div>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto">
				<div
					v-for="(theme, idx) in templateList"
					:key="theme.idx"
					class="flex flex-col gap-3"
				>
					<div
						class="m-1 aspect-video cursor-pointer overflow-hidden rounded-lg border border-gray-200 hover:border-gray-300"
						:class="getThemeThumbnailClasses(theme.name)"
						:style="getThemeThumbnailStyles(theme)"
						@click="performAction(theme.name)"
					>
						<SlidePreview
							v-if="shouldRenderPreview(theme)"
							:slide="getThemePreviewLayout(theme)"
							:scale="THEME_PREVIEW_SCALE"
						/>
					</div>
					<div class="flex">
						<LucideCheck
							v-if="props.update && theme.name == presentationTheme"
							class="size-4 stroke-[1.5] text-gray-800"
						/>
						<div class="select-none px-2 text-base text-gray-600">
							{{ theme.title }}
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { watch, nextTick, computed } from 'vue'
import { Dialog } from 'frappe-ui'

import SlidePreview from '@/components/SlidePreview.vue'
import { getThumbnailCardStyles } from '@/utils/helpers'
import { presentationTheme, templateList } from '@/stores/presentation'

const THEME_PREVIEW_SCALE = 310 / 960

const props = defineProps({
	update: {
		type: Boolean,
		default: false,
	},
})

const showThemeDialog = defineModel({
	name: 'showThemeDialog',
	required: true,
})

const emit = defineEmits(['create'])

const dialogTitle = computed(() => (props.update ? 'Set Theme' : 'Select Theme'))
const dialogDescription = computed(() =>
	props.update
		? 'Update the theme for this presentation. All newly added slides will use this theme.'
		: 'Select a theme for your new presentation. You can change this theme later.',
)

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
	return props.update && theme == presentationTheme.value
		? 'ring-2 ring-offset-1 ring-gray-400'
		: ''
}

const getThemePreviewLayout = (theme) => {
	const thumbnailIdx = ['Light', 'Dark'].includes(theme.title) ? 2 : 0
	return theme.layouts[thumbnailIdx] || theme.layouts[0]
}

const getThemeThumbnailStyles = (theme) => {
	const layout = getThemePreviewLayout(theme)
	return getThumbnailCardStyles(layout?.thumbnail)
}

const shouldRenderPreview = (theme) => {
	const layout = getThemePreviewLayout(theme)
	return layout && !layout.thumbnail
}
</script>
