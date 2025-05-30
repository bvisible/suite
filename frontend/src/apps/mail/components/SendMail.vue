<template>
	<component
		:is="isMobile ? SendMailMobileLayout : Dialog"
		v-model="show"
		:options="{ title: __('Send Mail'), size: '4xl' }"
	>
		<template #body-content>
			<TextEditor
				ref="textEditor"
				:editor-class="[
					'prose-sm max-w-none',
					'min-h-[15rem]',
					'[&_p.reply-to-content]:hidden',
				]"
				:content="mail.body"
				@change="(val: string) => (mail.body = val)"
			>
				<template #top>
					<div class="flex flex-col gap-3 border-b">
						<div class="flex items-center gap-2 sm:border-t sm:pt-2.5">
							<span class="text-xs text-gray-500">{{ __('From') }}:</span>
							<FormControl
								v-model="mail.from_email"
								type="autocomplete"
								:options="addressOptions.data || []"
							/>
						</div>
						<div class="flex items-center gap-2">
							<span class="text-xs text-gray-500">{{ __('To') }}:</span>
							<MultiselectInputControl
								v-model="mail.to"
								class="flex-1 text-sm"
								:validate="validateEmail"
								:error-message="
									(value: string) =>
										__(`'{0}' is an invalid email address`, [value])
								"
							/>
							<div class="flex gap-1.5">
								<Button
									:label="__('Cc')"
									variant="ghost"
									:class="[
										cc ? '!bg-gray-300 hover:bg-gray-200' : '!text-gray-500',
									]"
									@click="toggleCC()"
								/>
								<Button
									:label="__('Bcc')"
									variant="ghost"
									:class="[
										bcc ? '!bg-gray-300 hover:bg-gray-200' : '!text-gray-500',
									]"
									@click="toggleBCC()"
								/>
							</div>
						</div>
						<div v-if="cc" class="flex items-center gap-2">
							<span class="text-xs text-gray-500">{{ __('Cc') }}:</span>
							<MultiselectInputControl
								ref="ccInput"
								v-model="mail.cc"
								class="flex-1 text-sm"
								:validate="validateEmail"
								:error-message="
									(value: string) =>
										__(`'{0}' is an invalid email address`, [value])
								"
							/>
						</div>
						<div v-if="bcc" class="flex items-center gap-2">
							<span class="text-xs text-gray-500">{{ __('Bcc') }}:</span>
							<MultiselectInputControl
								ref="bccInput"
								v-model="mail.bcc"
								class="flex-1 text-sm"
								:validate="validateEmail"
								:error-message="
									(value: string) =>
										__(`'{0}' is an invalid email address`, [value])
								"
							/>
						</div>
						<div class="flex items-center gap-2 pb-2.5">
							<span class="text-xs text-gray-500">{{ __('Subject') }}:</span>
							<input
								v-model="mail.subject"
								class="text-ink-gray-8 flex-1 border-none bg-white text-base focus-visible:!ring-0"
							/>
						</div>
					</div>
				</template>
				<template #editor="{ editor }">
					<div
						class="flex h-[calc(100dvh-16.9rem)] flex-col overflow-y-auto py-2.5 text-sm sm:max-h-[40vh]"
						:class="{
							'h-[calc(100dvh-19.7rem)]': cc || bcc,
							'h-[calc(100dvh-21.9rem)]': cc && bcc,
						}"
					>
						<EditorContent :editor="editor" />

						<!-- Attachments -->
						<div class="mt-auto flex flex-col gap-2.5 pt-2.5 text-gray-700">
							<!-- <a
								v-for="(file, index) in attachments.data"
								:key="index"
								class="flex cursor-pointer items-center rounded bg-gray-100 p-2.5"
								:href="file.file_url"
								target="_blank"
							>
								<span class="mr-1 font-medium">
									{{ file.file_name || file.name }}
								</span>
								<span class="mr-1 font-extralight">
									({{ formatBytes(file.file_size) }})
								</span>
								<FeatherIcon
									class="ml-auto h-3.5 w-3.5"
									name="x"
									@click.stop.prevent=""
								/>
							</a> -->
						</div>
					</div>
				</template>
				<template #bottom>
					<FileUploader :class="{ 'fixed bottom-0 left-0 right-0 px-3': isMobile }">
						<template #default="{ file, progress, uploading, openFileSelector }">
							<div
								v-if="uploading"
								class="mb-2 rounded bg-gray-100 p-2.5 text-sm text-gray-700"
							>
								<div class="mb-1.5 flex items-center">
									<span class="mr-1 font-medium">
										{{ file.name }}
									</span>
									<span class="font-extralight">
										({{ formatBytes(file.size) }})
									</span>
								</div>
								<Progress :value="progress" />
							</div>

							<div
								class="flex flex-wrap justify-between gap-2 overflow-hidden border-t py-2.5"
							>
								<!-- Text Editor Buttons -->
								<div class="flex items-center gap-1 overflow-x-auto">
									<TextEditorFixedMenu :buttons="textEditorMenuButtons" />
									<EmojiPicker
										v-if="!isMobile"
										v-slot="{ togglePopover }"
										v-model="emoji"
										@update:model-value="() => appendEmoji()"
									>
										<Button variant="ghost" @click="togglePopover()">
											<template #icon>
												<Laugh class="h-4 w-4" />
											</template>
										</Button>
									</EmojiPicker>
									<Button variant="ghost" @click="openFileSelector()">
										<template #icon>
											<Paperclip class="h-4" />
										</template>
									</Button>
								</div>

								<!-- Send & Discard -->
								<div class="ml-auto flex items-center space-x-2 sm:mt-0">
									<Button :label="__('Discard')" @click="discardMail" />
									<Button
										variant="solid"
										:label="__('Send')"
										@click="sendMail"
									/>
								</div>
							</div>
						</template>
					</FileUploader>
				</template>
			</TextEditor>
		</template>
	</component>
</template>
<script setup lang="ts">
import { computed, inject, nextTick, reactive, ref, watch } from 'vue'
import { EditorContent } from '@tiptap/vue-3'
import { Laugh, Paperclip } from 'lucide-vue-next'
import {
	Button,
	Dialog,
	FeatherIcon,
	FileUploader,
	FormControl,
	Progress,
	TextEditor,
	TextEditorFixedMenu,
	createDocumentResource,
	createResource,
} from 'frappe-ui'

import { formatBytes, validateEmail } from '@/utils'
import { useScreenSize } from '@/utils/composables'
import MultiselectInputControl from '@/components/Controls/MultiselectInputControl.vue'
import EmojiPicker from '@/components/EmojiPicker.vue'
import SendMailMobileLayout from '@/components/SendMailMobileLayout.vue'

import type { EmailMessage, UserResource } from '@/types'

const show = defineModel<boolean>()

const { mailID, mailDetails } = defineProps<{ mailID?: string; mailDetails?: any }>()

const emit = defineEmits(['reloadMails'])

const user = inject('$user') as UserResource
const { isMobile } = useScreenSize()

const textEditor = ref(null)
const editor = computed(() => textEditor.value.editor)

const ccInput = ref(null)
const cc = ref(false)
const toggleCC = () => {
	cc.value = !cc.value
	if (cc.value) nextTick(() => ccInput.value.setFocus())
}

const bccInput = ref(null)
const bcc = ref(false)
const toggleBCC = () => {
	bcc.value = !bcc.value
	if (bcc.value) nextTick(() => bccInput.value.setFocus())
}

const emoji = ref()
const appendEmoji = () => {
	editor.value.commands.insertContent(emoji.value)
	editor.value.commands.focus()
	emoji.value = ''
}

const addressOptions = createResource({ url: 'mail.api.mail.get_user_addresses', auto: true })

const draftMail = ref()

const getDraftMail = (name: string) =>
	createDocumentResource({
		doctype: 'Email Message',
		name: name,
		onSuccess: (data: EmailMessage) => {
			Object.assign(mail, {
				from_email: data.from_email,
				to: data.recipients.filter((d) => d.type === 'To').map((d) => d.email),
				cc: data.recipients.filter((d) => d.type === 'Cc').map((d) => d.email),
				bcc: data.recipients.filter((d) => d.type === 'Bcc').map((d) => d.email),
				subject: data.subject,
				body: data.html_body,
			})
			cc.value = !!mail.cc?.length
			bcc.value = !!mail.bcc?.length
		},
		whitelistedMethods: { destroy: 'destroy' },
	})

watch(
	() => mailID,
	(val) => {
		if (val) draftMail.value = getDraftMail(val)
	},
)

const emptyMail = {
	from_email: user.data?.default_outgoing,
	to: [],
	cc: [],
	bcc: [],
	subject: '',
	body: '',
	in_reply_to: '',
	in_reply_to_id: '',
}
const mail = reactive({ ...emptyMail })

const createMail = createResource({
	url: 'mail.api.mail.create_mail',
	makeParams: ({ saveAsDraft }: { saveAsDraft: boolean }) => ({
		...mail,
		save_as_draft: saveAsDraft,
	}),
	onSuccess: () => setTimeout(() => emit('reloadMails'), 500),
})

const updateDraftMail = createResource({
	url: 'mail.api.mail.update_draft_mail',
	makeParams: ({ submit }: { submit: boolean }) => ({ ...mail, name: mailID, submit: submit }),
	onSuccess: () => setTimeout(() => emit('reloadMails'), 500),
})

const saveDraft = ref(true)

const sendMail = async () => {
	saveDraft.value = false
	show.value = false
	if (mailID) await updateDraftMail.submit({ submit: true })
	else await createMail.submit({ saveAsDraft: false })
	setTimeout(() => emit('reloadMails'), 500)
}

const discardMail = async () => {
	saveDraft.value = false
	show.value = false
	if (mailID) await draftMail.value.destroy.submit()
	setTimeout(() => emit('reloadMails'), 500)
}

const setMailDetails = () => {
	if (!mailDetails) return Object.assign(mail, emptyMail)

	mail.in_reply_to = mailDetails.in_reply_to
	mail.in_reply_to_id = mailDetails.in_reply_to_id
	mail.subject = mailDetails.subject
	mail.body = mailDetails.body
	mail.to = mailDetails.to
	mail.cc = mailDetails.cc
	mail.bcc = mailDetails.bcc

	cc.value = !!mail.cc?.length
	bcc.value = !!mail.bcc?.length
}

watch(show, (val) => {
	if (val) return setMailDetails()

	if (!saveDraft.value) return (saveDraft.value = true)

	if (mailID) updateDraftMail.submit({ submit: false })
	else if (!isMailEmpty.value) createMail.submit({ saveAsDraft: true })
})

const isMailEmpty = computed(() => {
	const isSubjectEmpty = !mail.subject.length
	let isBodyEmpty = true
	if (mail.body) {
		const element = document.createElement('div')
		element.innerHTML = mail.body
		isBodyEmpty =
			!element.textContent?.trim() &&
			Array.from(element.children).every((d) => !d.textContent?.trim())
	}
	const isRecipientsEmpty = [mail.to, mail.cc, mail.bcc].every((d) => !d.length)

	return isSubjectEmpty && isBodyEmpty && isRecipientsEmpty
})

const textEditorMenuButtons = [
	'Paragraph',
	['Heading 2', 'Heading 3', 'Heading 4', 'Heading 5', 'Heading 6'],
	'Separator',
	'Bold',
	'Italic',
	'FontColor',
	'Separator',
	'Align Left',
	'Align Center',
	'Align Right',
	'Separator',
	'Bullet List',
	'Numbered List',
	'Separator',
	// todo: fix inline image upload
	// 'Image',
	'Link',
	'Horizontal Rule',
	[
		'InsertTable',
		'AddColumnBefore',
		'AddColumnAfter',
		'DeleteColumn',
		'AddRowBefore',
		'AddRowAfter',
		'DeleteRow',
		'MergeCells',
		'SplitCell',
		'ToggleHeaderColumn',
		'ToggleHeaderRow',
		'ToggleHeaderCell',
		'DeleteTable',
	],
]
</script>
