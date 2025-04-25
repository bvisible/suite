<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs :items="[{ label: currentFolder }]">
			<template v-if="currentFolder !== 'Trash'" #suffix>
				<div class="ml-2 self-end text-xs text-gray-600">
					{{
						__('{0} {1}', [
							formatNumber(mailCount?.data || 0),
							mailCount?.data == 1 ? 'message' : 'messages',
						])
					}}
				</div>
			</template>
		</Breadcrumbs>
		<HeaderActions :current-folder="currentFolder" @reload-mails="reloadMails" />
	</header>
	<div class="relative flex h-[calc(100dvh-6rem)] sm:h-[calc(100dvh-3.05rem)]">
		<template v-if="mails[currentFolder].data?.length">
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
						<span v-else>{{ __('All Mail') }}</span>
					</div>
					<div class="flex items-center space-x-1.5 sm:space-x-3">
						<Tooltip
							v-if="!isMobile && !selections.length"
							:text="__('Select Layout')"
						>
							<Dropdown
								:options="[
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
								]"
							>
								<Button variant="ghost">
									<template #icon>
										<component
											:is="userLayout === 'full' ? Rows4 : PanelLeft"
											class="h-4 w-4 text-gray-600"
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
									<component :is="action.icon" class="h-4 w-4 text-gray-600" />
								</template>
							</Button>
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
				<div class="h-full overflow-y-auto overscroll-contain" @scroll="loadMoreEmails">
					<MailListItem
						v-for="(mail, idx) in mails[currentFolder].data"
						ref="mailItems"
						:key="idx"
						:mail
						:class="{ 'sm:bg-gray-100': mail.name == currentMail[currentFolder] }"
						@click="openMail(mail)"
						@select-mail="selectMail({ name: mail.name, mail_type: mail.mail_type })"
						@deselect-mail="deselectMail(mail.name)"
					/>
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
						!(currentMail[currentFolder] || route.params.id),
				}"
			>
				<MailThread
					ref="mailThread"
					:mail-i-d="currentMail[currentFolder]"
					:current-folder
					:type="getMailType() || doctype"
					@reload-mails="reloadMails"
					@mark-as-unread="
						setSeen.submit({
							mails: [
								{ name: currentMail[currentFolder], mail_type: getMailType() },
							],
							seen: 0,
						})
					"
					@set-thread-folders="
						(move_to_trash: boolean) =>
							setFolderForThreads.submit({
								threads: [
									{ name: currentMail[currentFolder], mail_type: getMailType() },
								],
								move_to_trash,
							})
					"
					@delete-thread="
						deleteThreads.submit([
							{ name: currentMail[currentFolder], mail_type: getMailType() },
						])
					"
				/>
			</div>
		</template>
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
	Mail as MailIcon,
	MailOpen,
	PanelLeft,
	RefreshCw,
	RotateCcw,
	Rows4,
	Trash2,
} from 'lucide-vue-next'
import {
	Breadcrumbs,
	Button,
	Checkbox,
	Dropdown,
	Tooltip,
	createListResource,
	createResource,
} from 'frappe-ui'

import { formatNumber, startResizing } from '@/utils'
import { useScreenSize } from '@/utils/composables'
import { userStore } from '@/stores/user'
import HeaderActions from '@/components/HeaderActions.vue'
import NoMails from '@/components/Icons/NoMails.vue'
import MailListItem from '@/components/MailListItem.vue'
import MailThread from '@/components/MailThread.vue'

import type { Folder, Mail, MailType, UserResource } from '@/types'

const { id } = defineProps<{ id?: string }>()

const socket = inject('$socket')
const user = inject('$user') as UserResource
const { currentMail, setCurrentMail } = userStore()
const route = useRoute()
const router = useRouter()
const { isMobile } = useScreenSize()

const currentFolder = computed(() => {
	const name = String(route.name)
	return (name.endsWith('Mail') ? name.replace('Mail', '') : name) as Folder
})

const doctype = computed(() =>
	['Inbox', 'Spam'].includes(currentFolder.value) ? 'Incoming Mail' : 'Outgoing Mail',
)

const mailThread = useTemplateRef('mailThread')

const folders: Folder[] = ['Inbox', 'Sent', 'Outbox', 'Drafts', 'Spam', 'Trash']

const createMailResource = (folder: Folder) =>
	createListResource({
		url: `mail.api.mail.get_${folder.toLowerCase()}_mails`,
		doctype: doctype.value,
		pageLength: 50,
		cache: [`${folder}Mails`, user.data?.name],
		onSuccess: (data: Mail[]) => {
			const mailExists = (id?: string | null) => data.some((m) => m.name === id)

			if (mailExists(id)) {
				if (currentMail[folder] !== id) setCurrentMail(folder, id ?? null)
				mailThread.value?.reload()
			} else if (mailExists(currentMail[folder])) {
				if (route.params.id !== currentMail[folder])
					router.replace({ name: `${folder}Mail`, params: { id: currentMail[folder] } })
				mailThread.value?.reload()
			} else setCurrentMail(folder, null)
		},
	})

const mails = Object.fromEntries(folders.map((folder) => [folder, createMailResource(folder)]))

const mailCountFilters = computed(() => ({
	folder: currentFolder.value,
	docstatus: ['!=', 2],
	[doctype.value === 'Incoming Mail' ? 'receiver' : 'sender']: user.data.name,
}))

const mailCount = createResource({
	url: 'frappe.client.get_count',
	auto: currentFolder.value !== 'Trash',
	makeParams: () => ({ doctype: doctype.value, filters: mailCountFilters.value }),
	cache: [`${currentFolder.value}MailCount`, user.data?.name],
})

const reloadMails = (folder: Folder = currentFolder.value) => {
	if (folder !== currentFolder.value) return
	mails[currentFolder.value].reload()
	if (currentFolder.value !== 'Trash') mailCount.reload()
	resetSelections()
}

interface SetSeenParams {
	names: string[]
	seen: 1 | 0
}

const setSeen = createResource({
	url: 'mail.api.mail.set_seen',
	makeParams: (values: SetSeenParams) => ({ ...values }),
	onSuccess: ({ names, seen }: SetSeenParams) => {
		names.forEach(
			(name) => (mails[currentFolder.value].data.find((m) => m.name === name).seen = seen),
		)
		if (!seen && names.includes(currentMail[currentFolder.value]))
			setCurrentMail(currentFolder.value, null)
	},
})

const setFolderForThreads = createResource({
	url: 'mail.api.mail.set_folder_for_threads',
	makeParams: ({ threads, move_to_trash }: { threads: string[]; move_to_trash: boolean }) => ({
		threads,
		move_to_trash,
	}),
	onSuccess: reloadMails,
})

const deleteThreads = createResource({
	url: 'mail.api.mail.delete_or_cancel_threads',
	makeParams: (threads: string[]) => ({ threads }),
	onSuccess: reloadMails,
})

// selection

const mailItems = useTemplateRef('mailItems')

interface Selection {
	name: string
	mail_type: MailType
}

const selections = ref<Selection[]>([])
const allSelectedManuallyToggled = ref(false)
const allSelected = ref(false)

const resetSelections = () => {
	allSelectedManuallyToggled.value = false
	allSelected.value = false
	mailItems.value?.forEach((item) => item?.setIsSelected(false))
	selections.value = []
}

const selectMail = (mail: Selection) => {
	if (!selections.value.includes(mail)) selections.value.push(mail)
}

const deselectMail = (mail: string) =>
	(selections.value = selections.value.filter((m) => m.name !== mail))

watch(
	() => selections.value.length,
	(val) => {
		allSelectedManuallyToggled.value = false
		allSelected.value = val === mails[currentFolder.value].data.length
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
				setFolderForThreads.submit({ threads: selections.value, move_to_trash: true }),
			icon: Trash2,
			condition: !!selections.value.length && currentFolder.value !== 'Trash',
		},
		{
			label: __('Delete Threads'),
			onClick: () => deleteThreads.submit(selections.value),
			icon: Trash2,
			condition: !!selections.value.length && currentFolder.value === 'Trash',
		},
		{
			label: __('Restore'),
			onClick: () =>
				setFolderForThreads.submit({ threads: selections.value, move_to_trash: false }),
			icon: RotateCcw,
			condition: !!selections.value.length && currentFolder.value === 'Trash',
		},
		{
			label: __('Mark as Read'),
			onClick: () => setSeen.submit({ mails: selections.value, seen: 1 }),
			icon: MailOpen,
			condition: !!selections.value.length,
		},
		{
			label: __('Mark as Unread'),
			onClick: () => setSeen.submit({ mails: selections.value, seen: 0 }),
			icon: MailIcon,
			condition: !!selections.value.length,
		},
		{
			label: __('Refresh'),
			onClick: () => reloadMails(),
			icon: RefreshCw,
			condition: !selections.value.length,
		},
	].filter((action) => action.condition),
)

watch(allSelected, (val) => {
	if (allSelectedManuallyToggled.value)
		mailItems.value?.forEach((item) => item?.setIsSelected(val))
})

const openMail = (mail: Mail) => {
	setCurrentMail(currentFolder.value, mail.name)
	if (!mail.seen)
		setSeen.submit({ mails: [{ name: mail.name, mail_type: mail.mail_type }], seen: 1 })
}

watch(() => currentFolder.value, reloadMails, { immediate: true })

onMounted(() => {
	socket.on('outgoing_mail_sent', () => reloadMails('Sent'))
	socket.on('incoming_mail_received', () => {
		reloadMails('Inbox')
		reloadMails('Spam')
	})
})

// layout

type LayoutType = 'split' | 'full'

const userLayout = ref<LayoutType>(
	(localStorage.getItem(`user:${user.data.name}:layout`) as LayoutType) || 'split',
)

const setUserLayout = (type: LayoutType) => {
	userLayout.value = type
	localStorage.setItem(`user:${user.data.name}:layout`, type)
}

const getMailType = () =>
	mails[currentFolder.value].data.find((m: Mail) => m.name === currentMail[currentFolder.value])
		?.mail_type

const loadMoreEmails = useDebounceFn(() => {
	if (mails[currentFolder.value].hasNextPage) mails[currentFolder.value].next()
}, 500)
</script>
