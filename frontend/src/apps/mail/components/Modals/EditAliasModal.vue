<template>
	<Dialog
		v-if="alias?.doc"
		v-model="show"
		:options="{
			title: aliasID,
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					disabled:
						JSON.stringify(alias.doc) === JSON.stringify(alias.originalDoc) ||
						!alias.doc.alias_for_name,
					onClick: alias.save.submit,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-4">
				<Switch v-model="alias.doc.enabled" :label="__('Enabled')" class="switch" />
				<FormControl
					v-model="alias.doc.alias_for_type"
					type="select"
					:label="__('Alias For Type')"
					:options="[
						{ label: __('Mail Account'), value: 'Mail Account' },
						{ label: __('Mail Group'), value: 'Mail Group' },
					]"
				/>
				<LinkControl
					v-model="alias.doc.alias_for_name"
					:label="
						__(
							alias.doc.alias_for_type === 'Mail Account'
								? 'Mail Account'
								: 'Mail Group',
						)
					"
					:doctype="
						alias.doc.alias_for_type === 'Mail Account' ? 'Mail Account' : 'Mail Group'
					"
					:filters="{ tenant: user.data.tenant, enabled: 1 }"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { inject, ref, watch } from 'vue'
import { Dialog, FormControl, Switch, createDocumentResource } from 'frappe-ui'

import { raiseToast } from '@/utils'
import LinkControl from '@/components/Controls/LinkControl.vue'

const show = defineModel<boolean>()

const props = defineProps<{ aliasID: string }>()

const emit = defineEmits(['reload-aliases'])

const user = inject('$user')

const alias = ref()

const getAlias = () =>
	createDocumentResource({
		doctype: 'Mail Alias',
		name: props.aliasID,
		transform: (data) => {
			data.enabled = !!data.enabled
		},
		setValue: {
			onSuccess: () => {
				show.value = false
				raiseToast(__('Alias saved successfully'))
				emit('reload-aliases')
			},
			onError: (error) => {
				raiseToast(error.messages[0], 'error')
				alias.value.reload()
			},
		},
	})

watch(
	show,
	(val) => {
		if (val) alias.value = getAlias()
	},
	{ immediate: true },
)

watch(
	() => alias.value.doc?.alias_for_type,
	(val) => {
		if (val) alias.value.doc.alias_for_name = ''
	},
)
</script>

<style>
.switch {
	@apply cursor-auto !p-0 hover:bg-white active:bg-white;
}
</style>
