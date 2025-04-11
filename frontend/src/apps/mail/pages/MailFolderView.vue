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
	<div class="flex h-[calc(100dvh-6rem)] sm:h-[calc(100dvh-3rem)]">
		<template v-if="mails[currentFolder].data?.length">
			<div ref="mailSidebar" class="sticky top-16 flex w-full flex-col border-r sm:w-1/3">
				<div class="flex items-center justify-between border-b px-3.5 py-2.5">
					<div class="text-base sm:px-2">
						<span v-if="selections.length">{{
							__('{0} {1} selected', [
								String(selections.length),
								selections.length === 1 ? 'item' : 'items',
							])
						}}</span>
						<span v-else>{{ __('All Mail') }}</span>
					</div>
					<div class="flex items-center space-x-2">
						<template v-if="selections.length">
							<Tooltip :text="__('Mark as read')">
								<Button
									variant="ghost"
									@click="setSeen.submit({ names: selections, seen: 1 })"
								>
									<template #icon>
										<MailOpen class="h-4 w-4 text-gray-600" />
									</template>
								</Button>
							</Tooltip>
							<Tooltip :text="__('Mark as unread')">
								<Button
									variant="ghost"
									@click="setSeen.submit({ names: selections, seen: 0 })"
								>
									<template #icon>
										<Mail class="h-4 w-4 text-gray-600" />
									</template>
								</Button>
							</Tooltip>
						</template>
						<Tooltip v-else :text="__('Refresh')">
							<Button variant="ghost" @click="reloadMails()">
								<template #icon>
									<RefreshCw class="h-4 w-4 text-gray-600" />
								</template>
							</Button>
						</Tooltip>
						<div class="flex items-center border-l pl-3.5">
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
					<SidebarDetail
						v-for="(mail, idx) in mails[currentFolder].data"
						ref="mailItems"
						:key="idx"
						:mail
						:class="{ 'sm:bg-gray-100': mail.name == currentMail[currentFolder] }"
						@click="openMail(mail)"
						@select-mail="selectMail(mail.name)"
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
				class="fixed inset-0 z-20 overflow-y-auto bg-white sm:static sm:z-0 sm:w-2/3"
				:class="{
					invisible:
						screenSize.width < 640 && !(currentMail[currentFolder] || route.params.id),
				}"
			>
				<MailThread
					ref="mailThread"
					:mail-i-d="currentMail[currentFolder]"
					:current-folder
					:type="getMailType() || doctype"
					@reload-mails="reloadMails"
					@mark-as-unread="
						setSeen.submit({ names: [currentMail[currentFolder]], seen: 0 })
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
import { Mail, MailOpen, RefreshCw } from 'lucide-vue-next'
import {
	Breadcrumbs,
	Button,
	Checkbox,
	Tooltip,
	createListResource,
	createResource,
} from 'frappe-ui'

import { formatNumber, startResizing } from '@/utils'
import { useScreenSize } from '@/utils/composables'
import { userStore } from '@/stores/user'
import HeaderActions from '@/components/HeaderActions.vue'
import NoMails from '@/components/Icons/NoMails.vue'
import MailThread from '@/components/MailThread.vue'
import SidebarDetail from '@/components/SidebarDetail.vue'

import type { Folder, UserResource } from '@/types'

const { id } = defineProps<{ id?: string }>()

const socket = inject('$socket')
const user = inject('$user') as UserResource
const { currentMail, setCurrentMail } = userStore()
const route = useRoute()
const router = useRouter()
const screenSize = useScreenSize()

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
		onSuccess: (data) => {
			const mailExists = (id?: string | null) => id && data.some((m) => m.name === id)

			if (mailExists(id)) {
				if (currentMail[folder] !== id) setCurrentMail(folder, id)
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

interface SetSeenParams {
	names: string[]
	seen: 1 | 0
}

const setSeen = createResource({
	url: 'mail.api.mail.set_seen',
	makeParams: (values: SetSeenParams) => ({
		mail_type: getMailType() || doctype.value,
		...values,
	}),
	onSuccess: ({ names, seen }: SetSeenParams) => {
		names.forEach(
			(name) => (mails[currentFolder.value].data.find((m) => m.name === name).seen = seen),
		)
		if (!seen && names.includes(currentMail[currentFolder.value]))
			setCurrentMail(currentFolder.value, null)
	},
})

// selection

const mailItems = useTemplateRef('mailItems')

const selections = ref([])
const allSelectedManuallyToggled = ref(false)
const allSelected = ref(false)

const resetSelections = () => {
	allSelectedManuallyToggled.value = false
	allSelected.value = false
	mailItems.value?.forEach((item) => item?.setIsSelected(false))
	selections.value = []
}

const selectMail = (mail) => {
	if (!selections.value.includes(mail)) selections.value.push(mail)
}

const deselectMail = (mail) => (selections.value = selections.value.filter((m) => m !== mail))

watch(
	() => selections.value.length,
	(val) => {
		allSelectedManuallyToggled.value = false
		allSelected.value = val === mails[currentFolder.value].data.length
	},
)

watch(allSelected, (val) => {
	if (allSelectedManuallyToggled.value)
		mailItems.value?.forEach((item) => item?.setIsSelected(val))
})

const openMail = (mail) => {
	setCurrentMail(currentFolder.value, mail.name)
	if (!mail.seen) setSeen.submit({ names: [mail.name], seen: 1 })
}

const reloadMails = (folder: Folder = currentFolder.value) => {
	if (folder !== currentFolder.value) return
	mails[currentFolder.value].reload()
	if (currentFolder.value !== 'Trash') mailCount.reload()
	resetSelections()
}

watch(() => currentFolder.value, reloadMails, { immediate: true })

onMounted(() => {
	socket.on('outgoing_mail_sent', () => reloadMails('Sent'))
	socket.on('incoming_mail_received', () => {
		reloadMails('Inbox')
		reloadMails('Spam')
	})
})

const getMailType = () =>
	mails[currentFolder.value].data.find((m) => m.name === currentMail[currentFolder.value])
		?.mail_type

const loadMoreEmails = useDebounceFn(() => {
	if (mails[currentFolder.value].hasNextPage) mails[currentFolder.value].next()
}, 500)
</script>
