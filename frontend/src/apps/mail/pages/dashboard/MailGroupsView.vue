<template>
	<DashboardLayout
		:breadcrumbs="[{ label: __('Groups') }]"
		:button-label="__('Add Group')"
		:button-action="() => (showAddGroup = true)"
	>
		<div class="flex items-center space-x-3">
			<FormControl v-model="search" :placeholder="__('Search')" class="w-80">
				<template #prefix>
					<FeatherIcon name="search" class="w-4 text-gray-600" />
				</template>
			</FormControl>
			<FormControl
				v-model="status"
				:placeholder="__('Status')"
				class="w-40"
				type="select"
				:options="STATUS_OPTIONS"
			/>
		</div>
		<ListView
			v-if="groups?.data"
			ref="listView"
			class="flex-1"
			:columns="LIST_COLUMNS"
			:rows="groups.data"
			:options="LIST_OPTIONS"
			row-key="name"
		>
			<ListHeader />
			<ListRows>
				<template v-if="groups.data.length">
					<ListRow
						v-for="row in groups.data"
						:key="row.name"
						v-slot="{ column, item }"
						:row="row"
					>
						<ListRowItem :item="item">
							<Badge
								v-if="column.key == 'enabled'"
								:theme="item ? 'green' : 'red'"
								:label="item ? 'Enabled' : 'Disabled'"
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
						@click="showDeleteGroups = true"
					/>
				</template>
			</ListSelectBanner>
		</ListView>
	</DashboardLayout>
	<AddGroupModal v-model="showAddGroup" @reload-groups="groups.reload()" />
	<Dialog v-model="showDeleteGroups" :options="deleteGroupsOptions" />
</template>

<script setup lang="ts">
import { inject, ref } from 'vue'
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
import DashboardLayout from '@/components/DashboardLayout.vue'
import AddGroupModal from '@/components/Modals/AddGroupModal.vue'

const user = inject('$user')

const listView = ref(null)

const search = ref('')
const debouncedSearch = useDebounce(search, 500)
const status = ref<'Enabled' | 'Disabled' | ''>('')

const showAddGroup = ref(false)
const showDeleteGroups = ref(false)

const groups = useList({
	doctype: 'Mail Group',
	fields: ['name', 'display_name', 'enabled'],
	filters: () => {
		const filters: Record<string, string | string[] | number> = {
			tenant: user.data?.tenant,
			name: ['like', debouncedSearch.value],
		}
		if (status.value) filters.enabled = status.value === 'Enabled' ? 1 : 0
		return filters
	},
	orderBy: 'email asc',
	limit: 100,
	cacheKey: ['mailTenantGroups', user.data?.tenant, debouncedSearch.value, status.value],
})

const deleteGroups = createResource({
	url: 'mail.api.admin.delete_groups',
	makeParams: () => ({ names: Array.from(listView.value?.selections) }),
	onSuccess: () => {
		groups.reload()
		showDeleteGroups.value = false
		raiseToast(__('Groups deleted successfully.'))
		listView.value?.toggleAllRows()
	},
	onError: (error) => {
		showDeleteGroups.value = false
		raiseToast(error.messages[0], 'error')
	},
})

const deleteGroupsOptions = {
	title: __('Delete Groups'),
	message: __('Are you sure you want to delete the selected groups?'),
	actions: [
		{
			label: __('Confirm'),
			variant: 'solid',
			onClick: deleteGroups.submit,
		},
	],
}

const LIST_COLUMNS = [
	{ label: __('Group Email'), key: 'name' },
	{ label: __('Display Name'), key: 'display_name' },
	{ label: __('Status'), key: 'enabled' },
]

const LIST_OPTIONS = {
	showTooltip: false,
	emptyState: { description: __('No groups found.') },
	getRowRoute: (row) => ({ name: 'Group', params: { groupName: row.name } }),
}

const STATUS_OPTIONS = [
	{ label: '', value: '' },
	{ label: __('Enabled'), value: 'Enabled' },
	{ label: __('Disabled'), value: 'Disabled' },
]
</script>
