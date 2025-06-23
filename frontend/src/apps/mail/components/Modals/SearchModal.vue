<template>
	<Dialog v-model="show" :options="{ size: '2xl', position: 'top' }">
		<template #body>
			<div class="flex items-center px-4 py-2">
				<Search class="h-4 w-4" />
				<input
					v-model="query"
					icon-left="search"
					type="text"
					class="placeholder-ink-gray-4 w-full border-none bg-transparent text-base focus:ring-0"
					placeholder="Search"
				/>
			</div>
			<div v-if="results?.data?.docs?.length" class="px-2 pb-2">
				<div
					v-for="(result, idx) in results?.data?.docs"
					:key="idx"
					class="flex items-center rounded p-2 hover:cursor-pointer hover:bg-gray-50"
					@click="openMail(result.mailbox_role, result.thread_id)"
				>
					<span class="text-base">{{ result.subject || __('[No subject]') }}</span>
					<span class="text-ink-gray-4 ml-auto text-sm">
						{{ getFormattedDate(result.received_at) }}
					</span>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { watchDebounced } from '@vueuse/core'
import { Search } from 'lucide-vue-next'
import { Dialog, createResource } from 'frappe-ui'

import { getFormattedDate } from '@/utils'
import { userStore } from '@/stores/user'

const show = defineModel<boolean>()

const query = ref('')

const results = createResource({
	url: 'mail.api.mail.search_mails',
	makeParams: () => ({ query: query.value }),
})

watchDebounced(
	() => query.value,
	() => {
		if (query.value) results.reload()
		else results.reset()
	},
	{ debounce: 200 },
)

const { setCurrentThread } = userStore()

const openMail = (mailbox: string, threadID: string) => {
	setCurrentThread(mailbox, threadID)
	query.value = ''
	show.value = false
}
</script>
