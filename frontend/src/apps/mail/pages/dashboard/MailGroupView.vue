<template>
	<div class="flex h-full flex-col">
		<header
			class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
		>
			<Breadcrumbs :items="BREADCRUMBS" />
			<Button
				:label="__('Add Member')"
				icon-left="user-plus"
				@click="showAddMember = true"
			/>
		</header>
		<div class="m-6 flex flex-1 flex-col">
			<ListView
				v-if="members?.data"
				ref="listView"
				class="flex-1"
				:columns="LIST_COLUMNS"
				:rows="members.data"
				:options="LIST_OPTIONS"
				row-key="name"
			>
				<ListHeader />
				<ListRows>
					<template v-if="members.data.length">
						<ListRow
							v-for="row in members.data"
							:key="row.name"
							v-slot="{ item }"
							:row="row"
						>
							<ListRowItem :item="item" />
						</ListRow>
					</template>
					<ListEmptyState v-else />
				</ListRows>
				<ListSelectBanner>
					<template #actions>
						<Button
							variant="ghost"
							theme="red"
							:label="__('Remove')"
							@click="showRemoveMembers = true"
						/>
					</template>
				</ListSelectBanner>
			</ListView>
		</div>
	</div>

	<Dialog v-model="showRemoveMembers" :options="removeMembersOptions" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import {
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

const props = defineProps<{ groupName: string }>()

const listView = ref(null)

const showAddMember = ref(false)
const showRemoveMembers = ref(false)

const LIST_COLUMNS = [
	{
		label: __('Name'),
		key: 'member_name',
	},
	{
		label: __('Type'),
		key: 'member_type',
	},
]

const LIST_OPTIONS = {
	showTooltip: false,
	emptyState: { description: __('No members have been added to this group.') },
}

const members = useList({
	doctype: 'Mail Group Member',
	fields: ['name', 'member_type', 'member_name'],
	filters: { mail_group: props.groupName },
	orderBy: 'member_name asc',
	limit: 100,
	cacheKey: ['mailGroupMembers', props.groupName],
})

const deleteMembers = createResource({
	url: 'mail.api.admin.delete_group_members',
	makeParams: () => ({ names: Array.from(listView.value?.selections) }),
	onSuccess: () => {
		members.reload()
		showRemoveMembers.value = false
		raiseToast(__('Members removed successfully.'))
		listView.value?.toggleAllRows()
	},
	onError: (error) => {
		showRemoveMembers.value = false
		raiseToast(error.messages[0], 'error')
	},
})

const removeMembersOptions = {
	title: __('Remove Members'),
	message: __('Are you sure you want to remove the selected members from this group?'),
	actions: [
		{
			label: __('Confirm'),
			variant: 'solid',
			onClick: deleteMembers.submit,
		},
	],
}
const BREADCRUMBS = [
	{ label: __('Groups'), route: { name: 'Groups' } },
	{ label: props.groupName },
]
</script>
