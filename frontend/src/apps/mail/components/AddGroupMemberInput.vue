<template>
	<div class="flex space-x-4">
		<LinkControl
			v-model="email"
			:placeholder="__('Email')"
			:doctype="type"
			:filters="{ tenant: user.data.tenant, name: ['not in', selectedMembers] }"
			class="flex-1"
			@update:model-value="(value: string) => emit('email-selected', value)"
		/>
		<Button icon="x" :disabled="isLastInput" @click="emit('remove-input', email)" />
	</div>
</template>

<script lang="ts" setup>
import { inject, ref } from 'vue'
import { Button } from 'frappe-ui'

import LinkControl from '@/components/Controls/LinkControl.vue'

import type { UserResource } from '@/types'

defineProps<{
	type: string
	selectedMembers: string[]
	isLastInput: boolean
}>()

const emit = defineEmits(['email-selected', 'remove-input'])

const user = inject('$user') as UserResource

const email = ref('')
</script>
