<template>
	<div class="flex h-full flex-col">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="[{ label: __('Mail Aliases') }]" />
			<Button :label="__('Add Mail Alias')" icon-left="plus" @click="showAddAlias = true" />
		</header>
		<div class="m-6 flex flex-1 flex-col">
			<ListView
				v-if="aliases?.data"
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
			</ListView>
		</div>
	</div>
	<!-- <AddAliasModal v-model="showAddAlias" @reload-aliases="aliases.reload()" /> -->
</template>

<script setup lang="ts">
import { inject, ref } from 'vue'
import {
	Badge,
	Breadcrumbs,
	Button,
	ListEmptyState,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListView,
} from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

// import AddAliasModal from '@/components/Modals/AddAliasModal.vue'

const user = inject('$user')

const showAddAlias = ref(false)

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
	selectable: false,
	showTooltip: false,
	emptyState: { description: __('No Mail Aliases created.') },
}

const aliases = useList({
	doctype: 'Mail Alias',
	fields: ['name', 'alias_for_name', 'enabled'],
	filters: { tenant: user.data?.tenant },
	limit: 100,
	cacheKey: ['mailTenantAliases', user.data?.tenant],
})
</script>
