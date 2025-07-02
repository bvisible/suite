<template>
	<Dialog v-model="show" :options="{ title: __('Settings'), size: '4xl' }">
		<template #body>
			<div class="flex" :style="{ height: 'calc(100vh - 9rem)' }">
				<div class="flex w-48 shrink-0 flex-col border-r bg-gray-50 p-4 py-3">
					<h1 class="px-2 text-xl leading-6">{{ __('Settings') }}</h1>
					<div class="mt-3 space-y-1">
						<button
							v-for="tab in tabs"
							:key="tab.label"
							class="flex h-7 w-full items-center gap-2 rounded px-2 py-1"
							:class="[
								activeTab.label == tab.label ? 'bg-gray-200' : 'hover:bg-gray-100',
							]"
							@click="activeTab = tab"
						>
							<component :is="tab.icon" class="h-4 w-4 stroke-[1.5] text-gray-700" />
							<span class="text-base text-gray-800"> {{ tab.label }} </span>
						</button>
					</div>
				</div>
				<div class="flex flex-1 flex-col space-y-5 overflow-y-auto p-12">
					<component :is="activeTab.component" v-if="activeTab" />
				</div>
				<Button
					class="absolute right-0 my-3 mr-4"
					variant="ghost"
					icon="x"
					@click="show = false"
				/>
			</div>
		</template>
	</Dialog>
</template>
<script setup lang="ts">
import { markRaw, ref } from 'vue'
import { Code, Mailbox, User } from 'lucide-vue-next'
import { Button, Dialog } from 'frappe-ui'

import AccountSettings from '@/components/Settings/AccountSettings.vue'
import AdvancedSettings from '@/components/Settings/AdvancedSettings.vue'
import ProfileSettings from '@/components/Settings/ProfileSettings.vue'

const show = defineModel<boolean>()

const tabs = [
	{
		label: __('Profile'),
		icon: User,
		component: markRaw(ProfileSettings),
	},
	{
		label: __('Account'),
		icon: Mailbox,
		component: markRaw(AccountSettings),
	},
	{
		label: __('Advanced'),
		icon: Code,
		component: markRaw(AdvancedSettings),
	},
]
const activeTab = ref(tabs[0])
</script>
