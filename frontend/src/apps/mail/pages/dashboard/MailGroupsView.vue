<template>
	<div class="flex h-full flex-col">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="[{ label: __('Groups') }]" />
			<Button :label="__('Add Group')" icon-left="plus" @click="showAddGroup = true" />
		</header>
		<div class="m-5 flex flex-1 flex-col">
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
		</div>
	</div>
	<AddGroupModal v-model="showAddGroup" @reload-groups="groups.reload()" />
	<Dialog v-model="showDeleteGroups" :options="deleteGroupsOptions" />
</template>

<script setup lang="ts">
import { inject, ref } from 'vue'
import {
	Badge,
	Breadcrumbs,
	Button,
	Dialog,
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
import AddGroupModal from '@/components/Modals/AddGroupModal.vue'

const user = inject('$user')

const listView = ref(null)

const showAddGroup = ref(false)
const showDeleteGroups = ref(false)

const LIST_COLUMNS = [
	{
		label: __('Group Email'),
		key: 'name',
	},
	{
		label: __('Display Name'),
		key: 'display_name',
	},
	{
		label: __('Status'),
		key: 'enabled',
	},
]

const LIST_OPTIONS = {
	showTooltip: false,
	emptyState: { description: __('No groups created.') },
	getRowRoute: (row) => ({ name: 'Group', params: { groupName: row.name } }),
}

const groups = useList({
	doctype: 'Mail Group',
	fields: ['name', 'display_name', 'enabled'],
	filters: { tenant: user.data?.tenant },
	orderBy: 'email asc',
	limit: 100,
	cacheKey: ['mailTenantGroups', user.data?.tenant],
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
</script>
