<template>
	<Dialog
		v-if="group?.doc"
		v-model="show"
		:options="{
			title: groupID,
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					disabled: JSON.stringify(group.doc) === JSON.stringify(group.originalDoc),
					onClick: group.save.submit,
				},
			],
		}"
	>
		<template #body-content>
			<Switch v-model="group.doc.enabled" :label="__('Enabled')" class="switch mb-4" />
			<FormControl v-model="group.doc.display_name" :label="__('Display Name')" />
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Dialog, FormControl, Switch, createDocumentResource } from 'frappe-ui'

import { raiseToast } from '@/utils'

const show = defineModel<boolean>()

const props = defineProps<{ groupID: string }>()

const emit = defineEmits(['reload-groups'])

const group = ref()

const getGroup = () =>
	createDocumentResource({
		doctype: 'Mail Group',
		name: props.groupID,
		transform: (data) => {
			data.enabled = !!data.enabled
		},
		setValue: {
			onSuccess: () => {
				show.value = false
				raiseToast(__('Group saved successfully'))
				emit('reload-groups')
			},
			onError: (error) => {
				raiseToast(error.messages[0], 'error')
				group.value.reload()
			},
		},
	})

watch(
	show,
	(val) => {
		if (val) group.value = getGroup()
	},
	{ immediate: true },
)
</script>

<style>
.switch {
	@apply cursor-auto !p-0 hover:bg-white active:bg-white;
}
</style>
