<template>
	<div class="flex h-screen flex-col">
		<header class="flex items-center border-b px-5 py-2.5">
			<Breadcrumbs :items="BREADCRUMBS" />
		</header>
		<div class="mx-auto my-5 rounded border p-12 sm:w-[75rem]">hi</div>
	</div>
</template>

<script setup lang="ts">
import { inject } from 'vue'
import { Breadcrumbs } from 'frappe-ui'

const { id } = defineProps<{ id: string }>()

const user = inject('$user')
const dayjs = inject('$dayjs')

const getTheme = (
	status: 'Draft' | 'Queued' | 'In Progress' | 'Completed' | 'Failed' | 'Cancelled',
) => {
	switch (status) {
		case 'Draft':
			return 'gray'
		case 'Completed':
			return 'green'
		case 'Failed':
		case 'Cancelled':
			return 'red'
		default:
			return 'blue'
	}
}

const BREADCRUMBS = [{ label: __('Mail Transfers'), route: '/mail-transfers' }, { label: id }]
</script>
