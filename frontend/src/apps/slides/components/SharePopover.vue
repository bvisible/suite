<template>
	<Popover :placement="'bottom-end'">
		<template #target="{ togglePopover }">
			<Button @click="openSharePopover(togglePopover)" label="Share">
				<template #prefix>
					<LucideShare2 class="size-4 stroke-[1.5]" />
				</template>
			</Button>
		</template>
		<template #body>
			<div class="my-1 flex w-[24rem] flex-col gap-2 rounded-lg bg-white p-4 shadow-xl">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2">
						<LucideEarth class="size-4 stroke-[1.5] text-gray-700" />
						<div class="text-base font-medium text-gray-900">Allow Public Access</div>
					</div>
					<Switch
						:modelValue="publicPresentation"
						@update:modelValue="(value) => updateAccessLevel(value)"
					/>
				</div>
				<div class="pl-0.5 text-sm text-gray-600">
					Anyone with the link can view this presentation.
				</div>
			</div>
		</template>
	</Popover>
</template>

<script setup>
import { ref } from 'vue'
import { Popover, Switch, call, toast } from 'frappe-ui'
import { presentationId, isPublicPresentation } from '@/stores/presentation'
import { resetFocus } from '@/stores/element'

const openSharePopover = async (togglePopover) => {
	await resetFocus()
	togglePopover()
}

const publicPresentation = ref(isPublicPresentation.value)

const updateAccessLevel = async (isPublic) => {
	if (!presentationId.value) return

	publicPresentation.value = isPublic

	call('slides.slides.doctype.presentation.presentation.set_public', {
		name: presentationId.value,
		is_public: isPublic,
	}).then(async () => {
		isPublicPresentation.value = isPublic
		toast.success('Access level updated')
	})
}
</script>
