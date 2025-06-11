<template>
	<button
		v-if="link"
		class="flex h-9 cursor-pointer items-center rounded text-gray-800 duration-300 ease-in-out focus:outline-none focus:transition-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-gray-400 sm:h-7"
		:class="isActive ? 'bg-white shadow-sm' : 'hover:bg-gray-100'"
		@click="openLink"
	>
		<div
			class="group flex w-full items-center duration-300 ease-in-out"
			:class="isCollapsed ? 'p-1' : 'px-2 py-1'"
		>
			<Tooltip :text="link.label" placement="right">
				<slot name="icon">
					<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
						<component
							:is="icons[link.icon]"
							class="stroke-1.5 h-4 w-4 text-gray-800"
						/>
					</span>
				</slot>
			</Tooltip>
			<span
				class="flex-shrink-0 text-base duration-300 ease-in-out"
				:class="
					isCollapsed ? 'ml-0 w-0 overflow-hidden opacity-0' : 'ml-2 w-auto opacity-100'
				"
			>
				{{ link.label }}
			</span>
			<span v-if="link.count && !isCollapsed" class="!ml-auto block text-xs text-gray-600">
				{{ link.count }}
			</span>
		</div>
	</button>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { type RouteLocationRaw, useRoute, useRouter } from 'vue-router'
import * as icons from 'lucide-vue-next'
import { Tooltip } from 'frappe-ui'

import { useScreenSize, useSidebar } from '@/utils/composables'

interface Link {
	label: string
	to?: RouteLocationRaw
	icon?: string
	count?: number
	activeFor?: string[]
}

const { link, isCollapsed = false } = defineProps<{
	link: Link
	isCollapsed?: boolean
}>()

const route = useRoute()
const router = useRouter()
const { isMobile } = useScreenSize()
const { closeSidebar } = useSidebar()

const isActive = computed(() =>
	link?.activeFor?.includes(
		['Mailbox', 'Mail'].includes(route.name) ? route.params.mailbox : route.name,
	),
)

const openLink = () => {
	if (!link.to) return
	router.push(link.to)
	if (isMobile.value) closeSidebar()
}
</script>
