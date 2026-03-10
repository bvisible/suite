<template>
	<Dialog
		v-model="showThemeDialog"
		class="pb-0"
		:options="{ size: '2xl' }"
		:disableOutsideClickToClose="!update"
	>
		<template #body-header>
			<div class="mb-6 flex items-center justify-between">
				<div class="select-none font-semibold">
					{{ dialogTitle }}
				</div>
				<Button v-if="update" variant="ghost" @click="showThemeDialog = false">
					<template #icon>
						<LucideX class="h-4 w-4 text-ink-gray-9" />
					</template>
				</Button>
			</div>
		</template>
		<template #body-content>
			<div class="mb-6 select-none text-base text-gray-600">{{ dialogDescription }}</div>
			<div class="grid max-h-[32rem] grid-cols-2 gap-6 overflow-y-auto">
				<div
					v-for="(theme, idx) in templateList"
					:key="theme.idx"
					class="flex flex-col gap-3"
				>
					<div
						class="m-1 aspect-video cursor-pointer rounded-lg border border-gray-200 hover:border-gray-300"
						:class="getThemeThumbnailClasses(theme.name)"
						:style="getThumbnailCardStyles(theme.layouts[0].thumbnail)"
						@click="performAction(theme.name)"
					></div>
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
import { watch, nextTick, onMounted, computed } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

import { getThumbnailCardStyles } from '@/utils/helpers'
import { presentationTheme, templateList } from '@/stores/presentation'

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

const dialogTitle = computed(() => (props.update ? 'Change Theme' : 'Select Theme'))
const dialogDescription = computed(() =>
	props.update
		? 'Update the theme for this presentation. All newly added slides will use this theme.'
		: 'Set a theme for your new presentation. You can change this theme later.',
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
</script>
