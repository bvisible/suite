<template>
	<div class="flex h-full flex-col">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="[{ label: __('Aliases') }]" />
			<Button :label="__('Add Alias')" icon-left="plus" @click="showAddAlias = true" />
		</header>
		<div class="m-6 flex flex-1 flex-col">
			<ListView
				v-if="aliases?.data"
				ref="listView"
				class="flex-1"
				:columns="LIST_COLUMNS"
				:rows="aliases.data"
				:options="LIST_OPTIONS"
				row-key="name"
			>
				<ListHeader />
				<ListRows>
					<template v-if="aliases.data.length">
						<ListRow
							v-for="row in aliases.data"
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
							@click="showDeleteAliases = true"
						/>
					</template>
				</ListSelectBanner>
			</ListView>
		</div>
	</div>
	<AddAliasModal v-model="showAddAlias" @reload-aliases="aliases.reload()" />
	<EditAliasModal
		v-if="selectedMailAlias"
		v-model="showEditAlias"
		:alias-i-d="selectedMailAlias"
		@reload-aliases="aliases.reload()"
	/>
	<Dialog v-model="showDeleteAliases" :options="deleteAliasesOptions" />
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
import AddAliasModal from '@/components/Modals/AddAliasModal.vue'
import EditAliasModal from '@/components/Modals/EditAliasModal.vue'

const user = inject('$user')

const listView = ref(null)

const selectedMailAlias = ref('')
const showAddAlias = ref(false)
const showEditAlias = ref(false)
const showDeleteAliases = ref(false)

const LIST_COLUMNS = [
	{
		label: __('Alias'),
		key: 'name',
	},
	{
		label: __('Alias For'),
		key: 'alias_for_name',
	},
	{
		label: __('Status'),
		key: 'enabled',
	},
]

const LIST_OPTIONS = {
	showTooltip: false,
	emptyState: { description: __('No aliases created.') },
	onRowClick: (row) => {
		selectedMailAlias.value = row.name
		showEditAlias.value = true
	},
}

const aliases = useList({
	doctype: 'Mail Alias',
	fields: ['name', 'alias_for_name', 'enabled'],
	filters: { tenant: user.data?.tenant },
	orderBy: 'email asc',
	limit: 100,
	cacheKey: ['mailTenantAliases', user.data?.tenant],
})

const deleteAliases = createResource({
	url: 'mail.api.admin.delete_aliases',
	makeParams: () => ({ names: Array.from(listView.value?.selections) }),
	onSuccess: () => {
		aliases.reload()
		showDeleteAliases.value = false
		raiseToast(__('Aliases deleted successfully.'))
		listView.value?.toggleAllRows()
	},
	onError: (error) => {
		showDeleteAliases.value = false
		raiseToast(error.messages[0], 'error')
	},
})

const deleteAliasesOptions = {
	title: __('Delete Aliases'),
	message: __('Are you sure you want to delete the selected aliases?'),
	actions: [
		{
			label: __('Confirm'),
			variant: 'solid',
			onClick: deleteAliases.submit,
		},
	],
}
</script>
