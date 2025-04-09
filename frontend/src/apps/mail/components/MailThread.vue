<template>
	<template v-if="mailID">
		<div class="flex items-center border-b px-3 py-2.5">
			<Button
				icon="chevron-left"
				variant="ghost"
				class="mr-2"
				@click="setCurrentMail(currentFolder, null)"
			/>
			<span
				v-if="mailThread.loading"
				:class="`bg-surface-gray-3 h-3.5 animate-pulse`"
				:style="{ width: generatePLaceholderWidth() }"
			/>
			<template v-else>
				<h2>{{ mailThread?.data?.[0].subject || __('[No subject]') }}</h2>
				<div class="ml-auto space-x-2">
					<Tooltip :text="__('Mark as unread')">
						<Button
							:icon="MessageSquareDot"
							variant="ghost"
							class="!text-ink-gray-6"
							@click="emit('markAsUnread')"
						/>
					</Tooltip>
				</div>
			</template>
		</div>
		<div v-if="mailThread.loading" class="animate-pulse space-y-4 px-2.5 py-3 sm:px-5 sm:py-6">
			<div v-for="i in Math.ceil(Math.random() * 4)" :key="i" class="rounded-md border p-3">
				<div class="flex space-x-3 border-b pb-2">
					<span class="bg-surface-gray-3 h-6.5 w-6.5 rounded-full" />
					<div class="flex flex-1 justify-between">
						<div class="flex flex-col space-y-1">
							<span class="bg-surface-gray-3 h-4 w-40" />
							<span class="bg-surface-gray-3 h-3 w-48" />
						</div>
						<div class="flex items-center space-x-2">
							<span class="bg-surface-gray-3 h-3 w-12 sm:w-20" />
							<span class="bg-surface-gray-3 h-3 w-3 rounded" />
							<span class="bg-surface-gray-3 h-3 w-3 rounded" />
						</div>
					</div>
				</div>
				<div class="mt-3 space-y-2">
					<div
						v-for="j in Math.ceil(Math.random() * 5)"
						:key="j"
						class="bg-surface-gray-3 h-2"
						:style="{ width: generatePLaceholderWidth() }"
					/>
				</div>
				<div v-if="Math.random() > 0.8" class="mt-5 flex flex-wrap space-x-2">
					<div
						v-for="k in Math.ceil(Math.random() * 3)"
						:key="k"
						class="bg-surface-gray-3 mb-2 h-6 w-24 rounded"
					/>
				</div>
			</div>
		</div>
		<div v-else class="space-y-4 px-2.5 py-3 sm:px-5 sm:py-6">
			<div
				v-for="mail in mailThread.data"
				:key="mail.name"
				class="p-3"
				:class="{
					'rounded-md border': mailThread.data.length > 1,
					'opacity-50': mail.folder === 'Trash',
				}"
			>
				<div class="flex space-x-3 border-b pb-2">
					<Avatar
						class="avatar border border-gray-300"
						:label="mail.display_name || mail.sender"
						:image="mail.user_image"
						size="xl"
					/>
					<div class="flex flex-1 justify-between text-xs">
						<div class="flex flex-col space-y-1">
							<div class="flex items-center space-x-1.5">
								<span class="text-base font-semibold">
									{{ mail.display_name || mail.from_ || mail.sender }}
								</span>
								<span
									v-if="mail.display_name && screenSize.width >= 640"
									class="text-gray-600"
								>
									{{ `<${mail.from_ || mail.sender}>` }}
								</span>
								<MailDetailsPopover :mail="mail" />
							</div>
							<div class="flex items-center space-x-2">
								<span class="flex items-center space-x-1">
									<span>{{ __('To: ') + toRecipient(mail) }}</span>
								</span>
								<span v-if="mail.cc.length">
									{{ __('Cc: ') + getRecipients(mail.cc) }}
								</span>
								<span v-if="mail.bcc.length">
									{{ __('Bcc: ') + getRecipients(mail.bcc) }}
								</span>
							</div>
						</div>
						<div class="flex items-center space-x-2 self-start">
							<MailDate
								:datetime="
									mail.folder === 'Drafts' ? mail.modified : mail.creation
								"
							/>
							<Tooltip
								v-for="action in mailActions(mail).filter(
									(d) => d.condition !== false,
								)"
								:key="action.label"
								:text="action.label"
							>
								<Button variant="ghost" @click="action.onClick()">
									<template #icon>
										<component
											:is="action.icon"
											class="h-4 w-4 text-gray-600"
										/>
									</template>
								</Button>
							</Tooltip>
							<Tooltip :text="__('More')">
								<Dropdown
									:options="
										moreActions(mail).filter((d) => d.condition !== false)
									"
								>
									<Button variant="ghost">
										<template #icon>
											<Ellipsis class="h-4 w-4 text-gray-600" />
										</template>
									</Button>
								</Dropdown>
							</Tooltip>
						</div>
					</div>
				</div>
				<div
					v-if="mail.body_html"
					class="mail-body ProseMirror prose-sm"
					v-html="mailBody(mail.body_html)"
				/>
				<pre v-else-if="mail.body_plain" class="mail-body text-wrap">{{
					mail.body_plain
				}}</pre>
				<div v-if="mail.attachments.length" class="mt-8 flex flex-wrap space-x-2">
					<AttachmentCapsule
						v-for="attachment in mail.attachments"
						:key="attachment.name"
						:file-name="attachment.file_name"
						:file-url="attachment.file_url"
						class="mb-2"
					/>
				</div>
			</div>
		</div>
		<SendMail
			v-model="showSendModal"
			:mail-i-d="draftMailID"
			:reply-details
			@reload-mails="emit('reloadMails', 'Drafts')"
		/>
	</template>
	<div v-else class="h-full overflow-hidden">
		<div class="m-4 flex h-[calc(100%-2em)] items-center justify-center rounded-md bg-gray-50">
			<div class="flex flex-col items-center space-y-3">
				<NoMailSelected class="h-16 w-16" />
				<p class="text-gray-500">
					{{ __('Select an email to view the thread.') }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { inject, reactive, ref, watch } from 'vue'
import {
	ArchiveRestore,
	Ellipsis,
	Forward,
	Mail,
	MessageSquareDot,
	Reply,
	ReplyAll,
	SquarePen,
	Trash2,
} from 'lucide-vue-next'
import { Avatar, Button, Dropdown, Tooltip, createResource } from 'frappe-ui'

import { getRecipients } from '@/utils'
import { useScreenSize } from '@/utils/composables'
import { userStore } from '@/stores/user'
import AttachmentCapsule from '@/components/AttachmentCapsule.vue'
import NoMailSelected from '@/components/Icons/NoMailSelected.vue'
import MailDate from '@/components/MailDate.vue'
import MailDetailsPopover from '@/components/MailDetailsPopover.vue'
import SendMail from '@/components/SendMail.vue'

import type { Folder } from '@/types'

const props = defineProps<{
	mailID: string | null
	currentFolder: Folder
	type?: 'Incoming Mail' | 'Outgoing Mail'
}>()

const emit = defineEmits(['reloadMails', 'markAsUnread'])

const screenSize = useScreenSize()
const dayjs = inject('$dayjs')
const { setCurrentMail } = userStore()

const showSendModal = ref(false)
const draftMailID = ref<string>()

const replyDetails = reactive({
	to: '',
	cc: '',
	bcc: '',
	subject: '',
	in_reply_to_mail_type: props.type,
	in_reply_to_mail_name: '',
})

const mailThread = createResource({
	url: 'mail.api.mail.get_mail_thread',
	makeParams: () => ({ name: props.mailID, mail_type: props.type }),
})

const reload = () => {
	if (props.mailID) mailThread.reload()
}

defineExpose({ reload })

const mailBody = (bodyHTML: string) => {
	bodyHTML = bodyHTML.replace(/<br\s*\/?>/, '')
	bodyHTML = bodyHTML.replace(
		/<blockquote>/g,
		'<div class="blockquote-container"><a href="#" class="font-medium text-gray-900 text-xs no-underline" onclick="this.nextElementSibling.style.display=\'block\'; this.style.display=\'none\'; return false;">Show more from this thread</a><blockquote style="display:none;">',
	)
	bodyHTML = bodyHTML.replace(/<\/blockquote>/g, '</blockquote></div>')
	return bodyHTML
}

type ActionType = 'editDraft' | 'reply' | 'replyAll' | 'forward'

interface MailAction {
	label: string
	onClick: () => void
	icon: typeof SquarePen
	condition?: boolean | (() => boolean)
}

const mailActions = (mail): MailAction[] => [
	{
		label: __('Edit Draft'),
		onClick: () => {
			draftMailID.value = mail.name
			showSendModal.value = true
		},
		icon: SquarePen,
		condition: mail.folder === 'Drafts',
	},
	{
		label: __('Reply'),
		onClick: () => openModal('reply', mail),
		icon: Reply,
		condition: mail.status !== 'Draft',
	},
]

const moreActions = (mail): MailAction[] => [
	{
		label: __('Reply All'),
		onClick: () => openModal('replyAll', mail),
		icon: ReplyAll,
		condition: () => mail.status !== 'Draft',
	},
	{
		label: __('Forward'),
		onClick: () => openModal('forward', mail),
		icon: Forward,
		condition: () => mail.status !== 'Draft',
	},
	{
		label: __('See MIME Message'),
		onClick: () => {
			window
				.open(
					`/mime-message/${mail.mail_type.toLowerCase().split(' ').join('-')}/${mail.name}`,
					'_blank',
				)
				?.focus()
		},
		icon: Mail,
		condition: () => mail.status !== 'Draft' && screenSize.width >= 640,
	},
	{
		label: __('Move to Trash'),
		onClick: () => setFolder.submit({ mail, moveToTrash: true }),
		icon: Trash2,
		condition: () => mail.folder !== 'Trash',
	},
	{
		label: __('Restore'),
		onClick: () => setFolder.submit({ mail, moveToTrash: false }),
		icon: ArchiveRestore,
		condition: () => mail.folder === 'Trash',
	},
	{
		label: __('Delete Message'),
		onClick: () => cancelMail.submit({ mail }),
		icon: Trash2,
		condition: () => mail.folder === 'Trash',
	},
]

interface SetFolderParams {
	mail: object
	moveToTrash: boolean
}

const setFolder = createResource({
	url: 'mail.api.mail.set_folder',
	method: 'POST',
	makeParams: (values: SetFolderParams) => ({
		mail_type: values.mail.mail_type,
		name: values.mail.name,
		move_to_trash: values.moveToTrash,
	}),
	onSuccess: () => emit('reloadMails'),
})

const cancelMail = createResource({
	url: 'mail.api.mail.cancel_mail',
	makeParams: (values: { mail: object }) => ({
		mail_type: values.mail.mail_type,
		name: values.mail.name,
	}),
	onSuccess: () => emit('reloadMails'),
})
const openModal = (type: ActionType, mail) => {
	if (props.type == 'Incoming Mail') {
		replyDetails.to = mail.reply_to || mail.sender
	} else {
		replyDetails.to = mail.to.map((to) => to.email).join(', ')
	}

	replyDetails.subject = mail.subject.startsWith('Re: ') ? mail.subject : `Re: ${mail.subject}`
	replyDetails.cc = ''
	replyDetails.bcc = ''
	replyDetails.in_reply_to_mail_name = mail.name

	if (type === 'replyAll') {
		replyDetails.cc = mail.cc.map((cc) => cc.email).join(', ')
		replyDetails.bcc = mail.bcc.map((bcc) => bcc.email).join(', ')
	}
	if (type === 'forward') {
		replyDetails.to = ''
		replyDetails.subject = `Fwd: ${mail.subject}`
	}
	replyDetails.html = getReplyHtml(mail.body_html, mail.creation)
	showSendModal.value = true
}

const getReplyHtml = (html, creation) => {
	const replyHeader = `
        On ${dayjs(creation).format('DD MMM YYYY')} at ${dayjs(creation).format('h:mm A')}, ${
			replyDetails.to
		} wrote:
    `
	return `<br><blockquote>${replyHeader} <br> ${html}</blockquote>`
}

const toRecipient = (mail) => {
	const isSoleRecipient = mail.to.length === 1 && !mail.cc.length && !mail.bcc.length
	if (!isSoleRecipient) return getRecipients(mail.to)

	return mail.to[0].display_name || mail.delivered_to || mail.to[0].email
}

const generatePLaceholderWidth = () => {
	const width = screenSize.width
	const max = width < 640 ? width - 50 : width / 2
	const min = width < 640 ? width / 2 : width / 3
	return `${Math.floor(Math.random() * (max - min + 1) + min)}px`
}

watch(() => props.mailID, reload)
</script>
<style>
.prose
	:where(blockquote p:first-of-type):not(
		:where([class~='not-prose'], [class~='not-prose'] *)
	)::before {
	content: '';
}

.mail-body {
	@apply prose prose-table:table-fixed prose-td:p-2 prose-th:p-2 prose-td:border prose-th:border prose-td:border-gray-300 prose-th:border-gray-300 prose-td:relative prose-th:relative prose-th:bg-gray-100 prose-sm max-w-none pt-4 text-sm leading-5;
}
</style>
