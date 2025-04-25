<template>
	<div
		class="flex cursor-pointer space-x-2.5 border-b px-3.5 py-2.5 sm:px-5"
		@mouseenter="isHovered = true"
		@mouseleave="isHovered = false"
	>
		<div class="flex h-8 min-h-8 min-w-8 justify-center">
			<Checkbox v-if="isHovered || isSelected" v-model="isSelected" size="md" @click.stop />
			<Avatar v-else :label="mail.display_name || mail.sender" size="xl" />
		</div>

		<div class="grow space-y-1 truncate">
			<div class="flex items-center justify-between">
				<h3 class="mr-1 mt-0.5 flex items-center truncate">
					<span
						v-if="!mail.seen"
						class="mr-1.5 min-h-2 min-w-2 rounded-full bg-blue-500"
					/>
					<span class="truncate text-base font-semibold">
						{{ mail.display_name || mail.sender }}
					</span>
				</h3>
				<MailDate :datetime="mail.creation" :in-list="true" />
			</div>
			<h4 class="truncate text-xs leading-[1.5]" :class="{ italic: !mail.subject }">
				{{ mail.subject || __('[No subject]') }}
			</h4>
			<h5
				class="truncate text-xs leading-[1.5] text-gray-600"
				:class="{ italic: !mail.snippet }"
			>
				{{ mail.snippet || __('— No message body —') }}
			</h5>
			<div
				v-if="mail.attachments.length || Object.keys(STATUS).includes(badgeField)"
				class="flex items-center"
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
					class="ml-auto"
					:label="badge.label"
					:theme="badge.theme"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Avatar, Badge, Checkbox } from 'frappe-ui'

import AttachmentCapsule from '@/components/AttachmentCapsule.vue'
import MailDate from '@/components/MailDate.vue'

import type { Mail } from '@/types'

const { mail } = defineProps<{ mail: Mail }>()

const emit = defineEmits(['select-mail', 'deselect-mail'])

const isHovered = ref(false)
const isSelected = ref(false)

watch(isSelected, () => emit(isSelected.value ? 'select-mail' : 'deselect-mail'))

const setIsSelected = (value: boolean) => (isSelected.value = value)

defineExpose({ setIsSelected })

interface BadgeType {
	label: string
	theme: 'gray' | 'blue' | 'green' | 'orange' | 'red'
}

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
