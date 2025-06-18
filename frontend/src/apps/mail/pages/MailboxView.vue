<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
	>
		<div class="flex items-center space-x-2">
			<Button v-if="isMobile" icon="menu" variant="ghost" @click="openSidebar" />
			<Breadcrumbs
				:items="[{ label: mailboxName, route: { name: 'Mailbox', params: { mailbox } } }]"
			>
				<template #suffix>
					<div class="ml-2 self-end text-xs text-gray-600">
						{{
							__('{0} {1}', [
								mailCount?.data || 0,
								mailCount?.data == 1 ? 'message' : 'messages',
							])
						}}
					</div>
				</template>
			</Breadcrumbs>
		</div>
		<HeaderActions :mailbox @reload-mails="reloadMails" />
	</header>

	<div class="relative flex h-[calc(100dvh-3.05rem)]">
		<template v-if="threads?.data?.length || filter">
			<div
				ref="mailSidebar"
				class="sticky top-16 flex flex-col border-r"
				:class="!isMobile && userLayout === 'split' ? 'w-1/3' : 'w-full'"
			>
				<div class="flex items-center justify-between border-b px-3.5 py-2.5 sm:px-5">
					<div class="text-base">
						<span v-if="selections.length">{{
							__('{0} {1} selected', [
								String(selections.length),
								selections.length === 1 ? 'item' : 'items',
							])
						}}</span>
						<span v-else>{{ title }}</span>
					</div>
					<div class="flex items-center space-x-1.5 sm:space-x-3">
						<Tooltip
							v-if="!isMobile && !selections.length"
							:text="__('Select Layout')"
						>
							<Dropdown :options="LAYOUT_OPTIONS">
								<Button variant="ghost">
									<template #icon>
										<component
											:is="userLayout === 'full' ? Rows4 : PanelLeft"
											class="text-ink-gray-7 h-4 w-4"
										/>
									</template>
								</Button>
							</Dropdown>
						</Tooltip>

						<Tooltip v-if="!selections.length" :text="__('Filter')">
							<Dropdown :options="FILTER_OPTIONS">
								<Button variant="ghost">
									<template #icon>
										<component
											:is="ListFilter"
											class="text-ink-gray-7 h-4 w-4"
										/>
									</template>
								</Button>
							</Dropdown>
						</Tooltip>

						<Tooltip
							v-for="action in selectActions"
							:key="action.label"
							:text="action.label"
						>
							<Button variant="ghost" @click="action.onClick">
								<template #icon>
									<component :is="action.icon" class="text-ink-gray-7 h-4 w-4" />
								</template>
							</Button>
						</Tooltip>

						<Tooltip
							v-if="!!selections.length && mailbox !== 'starred'"
							:text="__('Move To')"
						>
							<Dropdown :options="moveToOptions">
								<Button variant="ghost">
									<template #icon>
										<component
											:is="FolderInput"
											class="h-4 w-4 text-gray-600"
										/>
									</template>
								</Button>
							</Dropdown>
						</Tooltip>

						<div class="flex items-center border-l pl-3.5 sm:pl-5">
							<Tooltip :text="__('Select All')">
								<Checkbox
									v-model="allSelected"
									@change="allSelectedManuallyToggled = true"
								/>
							</Tooltip>
						</div>
					</div>
				</div>
				<div
					v-if="threads?.data?.length"
					class="h-full overflow-y-auto overscroll-contain"
					@scroll="loadMoreEmails"
				>
					<div v-for="(group, key) in groupedThreads" :key="key">
						<div class="text-ink-gray-6 border-b px-5 py-3.5 text-xs font-semibold">
							{{ formattedDate(key) }}
						</div>
						<MailListItem
							v-for="mail in group"
							ref="mailItems"
							:key="mail.thread_id"
							:mail
							:user-layout
							:class="{ 'bg-gray-50': mail.thread_id == threadID }"
							@click="openThread(mail)"
							@select-thread="selectThread(mail.thread_id)"
							@deselect-thread="deselectThread(mail.thread_id)"
						/>
					</div>
				</div>
				<div v-else class="flex h-full items-center justify-center">
					<p class="text-gray-500">
						{{ __('No mails found for the selected filter.') }}
					</p>
				</div>
			</div>
			<div class="flex cursor-col-resize justify-center" @mousedown="startResizing">
				<div
					ref="resizer"
					class="h-full rounded-full transition-all duration-300 ease-in-out group-hover:bg-gray-400"
				/>
			</div>
			<div
				class="overflow-y-auto bg-white"
				:class="{
					'w-2/3': !isMobile && userLayout === 'split',
					'absolute bottom-0 left-0 right-0 top-0 z-10':
						!isMobile && userLayout === 'full',
					'fixed inset-0 z-10': isMobile,
					hidden:
						(isMobile || userLayout === 'full') &&
						!(currentThread[mailbox] || route.params.threadID),
				}"
			>
				<MailThread
					ref="mailThread"
					:mailbox
					:thread-i-d
					@reload-mails="reloadMails"
					@mark-as-unread="setSeen.submit({ thread_ids: [threadID], seen: false })"
					@move-thread="
						(move_to_mailbox: string) =>
							moveThreads.submit({ thread_ids: [threadID], move_to_mailbox })
					"
					@delete-thread="deleteThreads.submit([threadID])"
				/>
			</div>
		</template>

		<!-- No mails -->
		<div v-else class="flex w-full flex-col items-center justify-center">
			<NoMails class="mb-2 h-16 w-16" />
			<p class="text-gray-500">
				{{ __('You have no mails in this folder.') }}
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import { computed, inject, onMounted, ref, useTemplateRef, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
	FolderInput,
	ListFilter,
	Mail,
	MailOpen,
	Mails,
	PanelLeft,
	Paperclip,
	RefreshCw,
	Rows4,
	Star,
	Trash2,
} from 'lucide-vue-next'
import { Breadcrumbs, Button, Checkbox, Dropdown, Tooltip, createResource } from 'frappe-ui'

import { startResizing } from '@/utils'
import { useScreenSize, useSidebar } from '@/utils/composables'
import { userStore } from '@/stores/user'
import HeaderActions from '@/components/HeaderActions.vue'
import NoMails from '@/components/Icons/NoMails.vue'
import MailListItem from '@/components/MailListItem.vue'
import MailThread from '@/components/MailThread.vue'

import type { LayoutType, Thread, UserResource } from '@/types'

const { mailbox, threadID } = defineProps<{ mailbox: string; threadID?: string }>()

const socket = inject('$socket')
const user = inject('$user') as UserResource
const dayjs = inject('$dayjs')
const { mailboxes, currentThread, setCurrentThread } = userStore()
const route = useRoute()
const router = useRouter()
const { isMobile } = useScreenSize()
const { openSidebar } = useSidebar()

const mailThread = useTemplateRef('mailThread')

const mailboxName = computed(() =>
	mailbox === 'starred'
		? __('Starred')
		: user.data.mailboxes.find((m) => m.role === mailbox)?.name,
)

const limit = ref(50)
const filter = ref<string | null>(null)

const title = computed(() => {
	switch (filter.value) {
		case 'unread':
			return __('Unread Mails')
		case 'starred':
			return __('Starred Mails')
		case 'has_attachments':
			return __('Mails With Attachments')
		default:
			return __('All Mails')
	}
})

const threads = createResource({
	url: 'mail.api.mail.get_mails_from_mailbox',
	makeParams: () => ({ mailbox, limit: limit.value, filter: filter.value }),
	onSuccess: (data: Thread[]) => {
		const threadExists = (threadID?: string | null) =>
			data.some((m) => m.thread_id === threadID)
		if (threadExists(threadID)) {
			if (currentThread[mailbox] !== threadID) setCurrentThread(mailbox, threadID ?? null)
			mailThread.value?.reload()
		} else if (threadExists(currentThread[mailbox])) {
			if (route.params.threadID !== currentThread[mailbox])
				router.replace({
					name: 'Mail',
					params: { mailbox: mailbox, threadID: currentThread[mailbox] },
				})
			mailThread.value?.reload()
		} else setCurrentThread(mailbox, null)
	},
})

const groupedThreads = computed(() =>
	threads?.data?.reduce((groups, thread) => {
		const date = dayjs(thread.received_at).format('YYYY-MM-DD')
		if (!groups[date]) groups[date] = []

		groups[date].push(thread)
		return groups
	}, {}),
)

const formattedDate = (date) => {
	if (dayjs(date).isToday()) return __('TODAY')
	if (dayjs(date).isYesterday()) return __('YESTERDAY')
	const isCurrentYear = dayjs(date).year() === dayjs().year()
	return dayjs(date)
		.format(isCurrentYear ? 'D MMMM' : 'D MMMM YYYY')
		.toUpperCase()
}

const mailCount = createResource({
	url: 'mail.api.mail.get_mailbox_thread_count',
	makeParams: () => ({ mailbox }),
	cache: [`${mailbox}MailCount`, user.data?.name],
})

const reloadMails = () => {
	threads.reload()
	mailCount.reload()
	mailboxes.reload()
	resetSelections()
}

interface SetSeenParams {
	thread_ids: string[]
	seen: boolean
}

const setSeen = createResource({
	url: 'mail.api.mail.set_seen',
	makeParams: (values: SetSeenParams) => ({ ...values, mailbox }),
	onSuccess: ({ thread_ids, seen }: SetSeenParams) => {
		mailboxes.reload()
		thread_ids.forEach(
			(name) => (threads.data.find((m: Thread) => m.thread_id === name).seen = Number(seen)),
		)
		if (
			!seen &&
			threads.data.some(
				(m: Thread) =>
					thread_ids.includes(m.thread_id) && m.thread_id === currentThread[mailbox],
			)
		)
			setCurrentThread(mailbox, null)
	},
})

const moveToOptions = computed(() =>
	user.data.mailboxes
		.filter((m) => ![mailbox, 'sent', 'drafts'].includes(m.role))
		.map((m) => ({
			label: m.name,
			onClick: () =>
				moveThreads.submit({ thread_ids: selections.value, move_to_mailbox: m.role }),
		})),
)

const moveThreads = createResource({
	url: 'mail.api.mail.set_threads_mailbox',
	makeParams: ({
		thread_ids,
		move_to_mailbox,
	}: {
		thread_ids: string[]
		move_to_mailbox: string
	}) => ({
		thread_ids,
		mailbox,
		move_to_mailbox,
	}),
	onSuccess: reloadMails,
})

const deleteThreads = createResource({
	url: 'mail.api.mail.delete_threads',
	makeParams: (thread_ids: string[]) => ({ thread_ids, mailbox }),
	onSuccess: reloadMails,
})

const fetchChanges = createResource({
	url: 'mail.api.mail.fetch_changes',
	onSuccess: reloadMails,
	onError: reloadMails,
})

// selection

const mailItems = useTemplateRef('mailItems')

const selections = ref<string[]>([])
const allSelectedManuallyToggled = ref(false)
const allSelected = ref(false)

const resetSelections = () => {
	allSelectedManuallyToggled.value = false
	allSelected.value = false
	mailItems.value?.forEach((item) => item?.setIsSelected(false))
	selections.value = []
}

const selectThread = (thread: string) => {
	if (!selections.value.includes(thread)) selections.value.push(thread)
}

const deselectThread = (thread: string) =>
	(selections.value = selections.value.filter((m) => m !== thread))

watch(
	() => selections.value.length,
	(val) => {
		allSelectedManuallyToggled.value = false
		allSelected.value = val === threads.data.length
	},
)

interface SelectAction {
	label: string
	onClick: () => void
	icon: typeof RefreshCw
	condition: boolean
}

const selectActions = computed((): SelectAction[] =>
	[
		{
			label: __('Move to Trash'),
			onClick: () =>
				moveThreads.submit({
					thread_ids: selections.value,
					mailbox,
					move_to_mailbox: 'trash',
				}),
			icon: Trash2,
			condition: !!selections.value.length && mailbox !== 'trash',
		},
		{
			label: __('Delete Threads'),
			onClick: () => deleteThreads.submit(selections.value),
			icon: Trash2,
			condition: !!selections.value.length && mailbox === 'trash',
		},
		{
			label: __('Mark as Read'),
			onClick: () => setSeen.submit({ thread_ids: selections.value, seen: true }),
			icon: MailOpen,
			condition: !!selections.value.length,
		},
		{
			label: __('Mark as Unread'),
			onClick: () => setSeen.submit({ thread_ids: selections.value, seen: false }),
			icon: Mail,
			condition: !!selections.value.length,
		},
		{
			label: __('Refresh'),
			onClick: () => fetchChanges.submit(),
			icon: RefreshCw,
			condition: !selections.value.length,
		},
	].filter((action) => action.condition),
)

watch(allSelected, (val) => {
	if (allSelectedManuallyToggled.value)
		mailItems.value?.forEach((item) => item?.setIsSelected(val))
})

const openThread = (mail: Thread) => {
	setCurrentThread(mailbox, mail.thread_id)
	if (!mail.seen) setSeen.submit({ thread_ids: [mail.thread_id], seen: true })
}

// filter

const FILTER_OPTIONS = [
	{
		label: __('All'),
		icon: Mails,
		onClick: () => setFilter(null),
	},
	{
		label: __('Unread'),
		icon: Mail,
		onClick: () => setFilter('unread'),
	},
	{
		label: __('Starred'),
		icon: Star,
		onClick: () => setFilter('starred'),
		condition: () => !['trash', 'starred'].includes(mailbox),
	},
	{
		label: __('Has attachments'),
		icon: Paperclip,
		onClick: () => setFilter('has_attachments'),
	},
]

const setFilter = (value: string | null) => {
	filter.value = value
	threads.reload()
	resetSelections()
}

// layout

const userLayout = ref<LayoutType>(
	(localStorage.getItem(`user:${user.data.name}:layout`) as LayoutType) || 'split',
)

const setUserLayout = (type: LayoutType) => {
	userLayout.value = type
	localStorage.setItem(`user:${user.data.name}:layout`, type)
}

const LAYOUT_OPTIONS = [
	{
		label: __('Full Width'),
		icon: Rows4,
		onClick: () => setUserLayout('full'),
	},
	{
		label: __('Vertical Split'),
		icon: PanelLeft,
		onClick: () => setUserLayout('split'),
	},
]

watch(
	() => mailbox,
	() => {
		filter.value = null
		reloadMails()
	},
	{ immediate: true },
)

onMounted(() =>
	socket.on('mail_created_or_updated', (updatedMailbox: string) => {
		if (updatedMailbox === mailbox) reloadMails()
		else if (['inbox', 'junk'].includes(updatedMailbox)) mailboxes.reload()
	}),
)

const loadMoreEmails = useDebounceFn(() => {
	if (threads?.data?.length === limit.value) {
		limit.value += 50
		threads.reload()
	}
}, 500)
</script>
