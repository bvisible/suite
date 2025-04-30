<template>
	<div class="flex items-center space-x-3">
		<FormControl v-model="search" :placeholder="__('Search')" class="w-80">
			<template #prefix>
				<FeatherIcon name="search" class="w-4 text-gray-600" />
			</template>
		</FormControl>
		<FormControl
			v-model="role"
			:placeholder="__('Assigned Role')"
			class="w-40"
			type="select"
			:options="ROLE_OPTIONS"
		/>
		<FormControl
			v-model="status"
			:placeholder="__('Invitation Status')"
			class="w-40"
			type="select"
			:options="STATUS_OPTIONS"
		/>
	</div>

	<ListView
		v-if="invites?.data"
		ref="listView"
		class="flex-1"
		:columns="LIST_COLUMNS"
		:rows="invites.data"
		:options="LIST_OPTIONS"
		row-key="name"
	>
		<ListHeader />
		<ListRows>
			<template v-if="invites.data.length">
				<ListRow
					v-for="row in invites.data"
					:key="row.name"
					v-slot="{ column, item }"
					:row="row"
				>
					<ListRowItem :item="item">
						<Badge
							v-if="column.key == 'is_admin'"
							:label="__(item ? 'Mail Admin' : 'Mail User')"
							:theme="item ? 'blue' : 'gray'"
						/>
						<Badge
							v-else-if="column.key == 'status'"
							:label="item"
							:theme="getTheme(item)"
						/>
					</ListRowItem>
				</ListRow>
			</template>
			<ListEmptyState v-else />
		</ListRows>
		<ListSelectBanner>
			<template #actions>
				<Button
					variant="ghost"
					theme="red"
					:label="__('Delete')"
					@click="showDeleteInvites = true"
				/>
			</template>
		</ListSelectBanner>
	</ListView>

	<Dialog v-model="showDeleteInvites" :options="DELETE_INVITES_OPTIONS" />
</template>

<script setup lang="ts">
import { inject, ref, useTemplateRef } from 'vue'
import { useDebounce } from '@vueuse/core'
import {
	Badge,
	Button,
	Dialog,
	FeatherIcon,
	FormControl,
	ListEmptyState,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListSelectBanner,
	ListView,
	createResource,
} from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

import { raiseToast } from '@/utils'

const user = inject('$user')

const search = ref('')
const debouncedSearch = useDebounce(search, 500)
const role = ref<'Mail User' | 'Mail Admin' | ''>('')
const status = ref<'Pending' | 'Accepted' | 'Expired' | ''>('')
const showDeleteInvites = ref(false)

const invites = useList({
	doctype: 'Mail Account Request',
	fields: ['name', 'email', 'account', 'is_admin', 'is_verified', 'is_expired'],
	filters: () => {
		const filters: Record<string, string | string[] | number> = {
			tenant: user.data?.tenant,
			is_invite: 1,
			send_invite: 1,
			account: ['like', debouncedSearch.value],
		}

		if (role.value) filters.is_admin = Number(role.value === 'Mail Admin')
		if (status.value === 'Accepted') filters.is_verified = 1
		else if (status.value === 'Pending') filters.is_expired = filters.is_verified = 0
		else if (status.value === 'Expired') {
			filters.is_expired = 1
			filters.is_verified = 0
		}

		return filters
	},
	transform: (data) =>
		data.map((row) => ({
			...row,
			status: row.is_verified ? 'Accepted' : row.is_expired ? 'Expired' : 'Pending',
		})),
	limit: 100,
	cacheKey: [
		'memberInvites',
		user.data?.tenant,
		debouncedSearch.value,
		role.value,
		status.value,
	],
})

const reloadInvites = () => invites.reload()
defineExpose({ reloadInvites })

const listView = useTemplateRef('listView')

const deleteInvites = createResource({
	url: 'mail.api.admin.delete_account_requests',
	makeParams: () => ({ names: Array.from(listView.value?.selections) }),
	onSuccess: () => {
		invites.reload()
		showDeleteInvites.value = false
		raiseToast(__('Invites deleted successfully.'))
		listView.value?.toggleAllRows()
	},
	onError: (error) => {
		showDeleteInvites.value = false
		raiseToast(error.messages[0], 'error')
	},
})

const DELETE_INVITES_OPTIONS = {
	title: __('Delete Invites'),
	message: __(
		'Are you sure you want to delete the selected invites? This will invalidate them for the recipients if pending.',
	),
	actions: [{ label: __('Confirm'), variant: 'solid', onClick: deleteInvites.submit }],
}

const LIST_COLUMNS = [
	{ label: __('Assigned Email'), key: 'account' },
	{ label: __('Backup Email'), key: 'email' },
	{ label: __('Assigned Role'), key: 'is_admin' },
	{ label: __('Invitation Status'), key: 'status' },
]

const LIST_OPTIONS = {
	showTooltip: false,
	rowHeight: 50,
	emptyState: { description: __('No invites found.') },
}

const ROLE_OPTIONS = [
	{ label: '', value: '' },
	{ label: __('Mail User'), value: 'Mail User' },
	{ label: __('Mail Admin'), value: 'Mail Admin' },
]

const STATUS_OPTIONS = [
	{ label: '', value: '' },
	{ label: __('Pending'), value: 'Pending' },
	{ label: __('Accepted'), value: 'Accepted' },
	{ label: __('Expired'), value: 'Expired' },
]

const getTheme = (status: 'Accepted' | 'Expired' | 'Pending') =>
	status === 'Accepted' ? 'green' : status === 'Expired' ? 'gray' : 'orange'
</script>
