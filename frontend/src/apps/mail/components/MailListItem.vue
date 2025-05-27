<template>
	<div
		class="flex cursor-pointer space-x-2.5 border-b px-3.5 py-2.5 sm:px-5 sm:hover:bg-gray-50"
		:class="{ '!bg-blue-50': isSelected, '!py-2': isFullWidth }"
		@mouseenter="isHovered = true"
		@mouseleave="isHovered = false"
	>
		<div class="flex h-8 min-h-8 min-w-8 items-center justify-center">
			<Checkbox v-if="isHovered || isSelected" v-model="isSelected" size="md" @click.stop />
			<Avatar
				v-else
				:label="mail.from_name || mail.from_email"
				:size="isFullWidth ? 'lg' : 'xl'"
			/>
		</div>

		<div
			class="grow truncate"
			:class="isFullWidth ? 'flex items-center space-x-3' : 'space-y-1'"
		>
			<div
				class="flex items-center"
				:class="isFullWidth ? 'min-w-36 max-w-36' : 'justify-between'"
			>
				<h3 class="mr-1 mt-0.5 flex items-center truncate">
					<span
						v-if="!mail.seen"
						class="mr-1.5 min-h-2 min-w-2 rounded-full bg-blue-500"
					/>
					<span class="truncate text-base font-semibold">
						{{ mail.from_name || mail.from_email }}
					</span>
				</h3>
				<MailDate v-if="!isFullWidth" :datetime="mail.received_at" :in-list="true" />
			</div>
			<h4
				class="truncate text-sm leading-[1.5]"
				:class="{ italic: !mail.subject, '!text-base': isFullWidth }"
			>
				{{ mail.subject || __('[No subject]') }}
			</h4>
			<h5
				class="truncate text-sm leading-[1.5] text-gray-600"
				:class="{ italic: !mail.preview, 'min-w-0 flex-1 !text-base': isFullWidth }"
			>
				{{ mail.preview || __('— No message body —') }}
			</h5>
			<div
				v-if="mail.attachments || Object.keys(STATUS).includes(badgeField)"
				class="flex items-center"
				:class="{ 'ml-auto min-w-fit': isFullWidth }"
			>
				<AttachmentCapsule
					v-for="attachment in mail.attachments.slice(0, 2)"
					:key="attachment.name"
					:file-name="attachment.file_name"
					class="mr-2 max-w-32"
				/>
				<AttachmentCapsule
					v-if="mail.attachments.length > 2"
					:file-name="__('+{0} more', [String(mail.attachments.length - 2)])"
				/>
				<Badge
					v-if="Object.keys(STATUS).includes(badgeField)"
					variant="outline"
					:class="isFullWidth ? 'ml-5' : 'ml-auto'"
					:label="badge.label"
					:theme="badge.theme"
				/>
			</div>
			<div v-if="isFullWidth" class="flex min-w-20 max-w-20 justify-end">
				<MailDate :datetime="mail.received_at" :in-list="true" />
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Avatar, Badge, Checkbox } from 'frappe-ui'

import { useScreenSize } from '@/utils/composables'
import AttachmentCapsule from '@/components/AttachmentCapsule.vue'
import MailDate from '@/components/MailDate.vue'

import type { LayoutType } from '@/types'

const { mail, userLayout } = defineProps<{ mail: any; userLayout: LayoutType }>()

const emit = defineEmits(['select-thread', 'deselect-thread'])

const { isMobile } = useScreenSize()

const isFullWidth = computed(() => userLayout === 'full' && !isMobile.value)

const isHovered = ref(false)
const isSelected = ref(false)

watch(isSelected, () => emit(isSelected.value ? 'select-thread' : 'deselect-thread'))

const setIsSelected = (value: boolean) => (isSelected.value = value)

defineExpose({ setIsSelected })

interface BadgeType {
	label: string
	theme: 'gray' | 'blue' | 'green' | 'orange' | 'red'
}

// TODO:

const STATUS = {
	Draft: { label: __('Draft'), theme: 'gray' },
	Queued: { label: __('Queued'), theme: 'orange' },
	Blocked: { label: __('Blocked'), theme: 'red' },
	Failed: { label: __('Failed'), theme: 'red' },
	'DSN Report': { label: __('DSN Report'), theme: 'blue' },
	'DMARC Report': { label: __('DMARC Report'), theme: 'blue' },
}

const badgeField = computed(() => (mail.mail_type === 'Outgoing Mail' ? mail.status : mail.type))

const badge = computed<BadgeType>(() => STATUS[badgeField.value])
</script>
