<template>
	<DashboardLayout
		v-if="list.originalDoc"
		:breadcrumbs="BREADCRUMBS"
		:badge-label="list.originalDoc.enabled ? 'Enabled' : 'Disabled'"
		:badge-theme="list.originalDoc.enabled ? 'green' : 'red'"
	>
		<template #actions>
			<Dropdown :options="ADD_OPTIONS">
				<Button icon="plus" :disabled="!list.originalDoc.enabled" />
			</Dropdown>
			<Button
				variant="solid"
				:label="__('Save')"
				:loading="list.save.loading"
				:disabled="JSON.stringify(list.doc) === JSON.stringify(list.originalDoc)"
				@click="list.save.submit()"
			/>
		</template>
		<template #default>
			<div v-if="list.doc" class="grid grid-cols-1 rounded-md border sm:grid-cols-2">
				<div class="border-r p-4">
					<Switch v-model="list.doc.enabled" :label="__('Enabled')" />
				</div>
				<div class="my-1.5 p-4">
					<HorizontalControl :label="__('Display Name')">
						<FormControl v-model="list.doc.display_name" />
					</HorizontalControl>
				</div>
			</div>
			<div class="flex flex-1 flex-col space-y-4 rounded-md border p-4">
				<div class="flex items-center space-x-3">
					<FormControl v-model="search" :placeholder="__('Search')" class="w-80">
						<template #prefix>
							<FeatherIcon name="search" class="w-4 text-gray-600" />
						</template>
					</FormControl>
					<FormControl
						v-model="type"
						:placeholder="__('Type')"
						class="w-40"
						type="select"
						:options="TYPE_OPTIONS"
					/>
				</div>
				<ListView
					v-if="members?.data"
					ref="listView"
					:columns="LIST_COLUMNS"
					:rows="members.data"
					:options="LIST_OPTIONS"
					row-key="name"
					class="flex-1"
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
		</template>
	</DashboardLayout>

	<AddMailingListMembersModal
		v-model="showAddMembers"
		:list="listName"
		:type="addType"
		@reload-members="members.reload()"
	/>
	<Dialog v-model="showRemoveMembers" :options="removeMembersOptions" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounce } from '@vueuse/core'
import { User, Users } from 'lucide-vue-next'
import {
	Button,
	Dialog,
	Dropdown,
	FeatherIcon,
	FormControl,
	ListEmptyState,
	ListHeader,
	ListRow,
	ListRowItem,
	ListRows,
	ListSelectBanner,
	ListView,
	Switch,
	createDocumentResource,
	createResource,
} from 'frappe-ui'
import { useList } from 'frappe-ui/src/data-fetching'

import { raiseToast } from '@/utils'
import HorizontalControl from '@/components/Controls/HorizontalControl.vue'
import DashboardLayout from '@/components/DashboardLayout.vue'
import AddMailingListMembersModal from '@/components/Modals/AddMailingListMembersModal.vue'

import type { MailingList } from '@/types'

const { listName } = defineProps<{ listName: string }>()

const router = useRouter()

const listView = ref(null)

const search = ref('')
const debouncedSearch = useDebounce(search, 500)
const type = ref<'Mail Account' | 'Mail Group' | ''>('')

const addType = ref<'Mail Account' | 'Mail Group'>('Mail Account')
const showAddMembers = ref(false)
const showRemoveMembers = ref(false)

const list = createDocumentResource({
	doctype: 'Mailing List',
	name: listName,
	transform: (data: MailingList) => {
		data['enabled'] = !!data['enabled']
	},
	setValue: {
		onSuccess: () => raiseToast(__('Mailing List settings saved successfully')),
		onError(error) {
			raiseToast(error.messages[0], 'error')
			list.reload()
		},
	},
	onError: () => router.replace({ name: 'MailingLists' }),
})

const members = useList({
	doctype: 'Mailing List Member',
	fields: ['name', 'member_type', 'member_name'],
	filters: () => {
		const filters: Record<string, string | string[]> = {
			mailing_list: listName,
			member_name: ['like', `%${debouncedSearch.value}%`],
		}
		if (type.value) filters.member_type = type.value
		return filters
	},
	orderBy: 'member_name asc',
	limit: 100,
	transform: (data) =>
		data.map((row) => ({
			...row,
			member_type: row.member_type === 'Mail Account' ? 'User' : 'Group',
		})),
	cacheKey: ['mailingListMembers', listName, debouncedSearch.value, type.value],
})

const deleteMembers = createResource({
	url: 'mail.api.admin.delete_list_members',
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
	message: __('Are you sure you want to remove the selected members from this list?'),
	actions: [
		{
			label: __('Confirm'),
			variant: 'solid',
			onClick: deleteMembers.submit,
		},
	],
}
const BREADCRUMBS = [
	{ label: __('Mailing Lists'), route: '/dashboard/mailing-lists' },
	{ label: listName },
]

const LIST_COLUMNS = [
	{ label: __('Name'), key: 'member_name' },
	{ label: __('Type'), key: 'member_type' },
]

const LIST_OPTIONS = {
	showTooltip: false,
	emptyState: { description: __('No members found.') },
}

const ADD_OPTIONS = [
	{
		label: __('Add Members'),
		icon: User,
		onClick: () => {
			addType.value = 'Mail Account'
			showAddMembers.value = true
		},
	},
	{
		label: __('Add Groups'),
		icon: Users,
		condition: () => false,
		onClick: () => {
			addType.value = 'Mail Group'
			showAddMembers.value = true
		},
	},
]

const TYPE_OPTIONS = [
	{ label: '', value: '' },
	{ label: __('User'), value: 'Mail Account' },
	{ label: __('Group'), value: 'Mail Group' },
]
</script>
