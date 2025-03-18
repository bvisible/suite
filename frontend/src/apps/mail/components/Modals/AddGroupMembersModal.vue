<template>
	<Dialog
		v-model="show"
		:options="{
			title: type === 'Mail Account' ? __('Add Members') : __('Add Groups'),
			actions: [
				{
					label: __('Confirm'),
					variant: 'solid',
					disabled: members.length === 0,
					onClick: addMembers.submit,
				},
			],
		}"
	>
		<template #body-content>
			<div ref="dialogBody" class="max-h-80 space-y-4 overflow-y-auto">
				<AddGroupMemberInput
					v-for="(inputId, index) in inputFields"
					:key="inputId"
					:type="type"
					:selected-members="members"
					:is-last-input="index === inputFields.length - 1"
					@email-selected="(email) => handleEmailSelected(email, index)"
					@remove-input="(email) => removeInput(email, index)"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

import { raiseToast } from '@/utils'
import AddGroupMemberInput from '@/components/AddGroupMemberInput.vue'

const { group, type } = defineProps<{ group: string; type: 'Mail Account' | 'Mail Group' }>()

const emit = defineEmits(['reloadMembers'])

const show = defineModel<boolean>()

const dialogBody = ref<HTMLElement | null>(null)

const inputFields = ref([0])
const members = ref<string[]>([])

const handleEmailSelected = (email: string, index: number) => {
	members.value.push(email)
	if (index === inputFields.value.length - 1) addInput()
}

const addInput = () => {
	inputFields.value.push(inputFields.value.length)
	nextTick(() => {
		if (dialogBody.value)
			dialogBody.value.scrollTo({ top: dialogBody.value.scrollHeight, behavior: 'smooth' })
	})
}

const removeInput = (email: string, index: number) => {
	members.value = members.value.filter((member) => member !== email)
	inputFields.value.splice(index, 1)
}

const addMembers = createResource({
	url: 'mail.api.admin.add_group_members',
	makeParams: () => ({ group, type, members: members.value }),
	onSuccess: () => {
		raiseToast(__('Members added successfully'))
		show.value = false
		emit('reloadMembers')
	},
	onError: (error) => raiseToast(error.message, 'error'),
})

watch(
	() => show.value,
	(val) => {
		if (!val) return
		members.value = []
		inputFields.value = [0]
	},
)
</script>
