<template>
	<button
		v-if="link && !link.onlyMobile"
		class="flex h-7 cursor-pointer items-center rounded text-gray-800 duration-300 ease-in-out focus:outline-none focus:transition-none focus-visible:rounded focus-visible:ring-2 focus-visible:ring-gray-400"
		:class="isActive ? 'bg-white shadow-sm' : 'hover:bg-gray-100'"
		@click="link.to && $router.push(link.to)"
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
			<span v-if="link.count" class="!ml-auto block text-xs text-gray-600">
				{{ link.count }}
			</span>
			<div
				v-if="showControls"
				class="invisible !ml-auto block flex items-center space-x-2 text-xs text-gray-600 group-hover:visible"
			>
				<component
					:is="icons['Edit']"
					class="stroke-1.5 h-3 w-3 text-gray-800"
					@click.stop="openModal(link)"
				/>
				<component
					:is="icons['X']"
					class="stroke-1.5 h-3 w-3 text-gray-800"
					@click.stop="deletePage(link)"
				/>
			</div>
		</div>
	</button>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { type RouteLocationRaw, useRoute } from 'vue-router'
import * as icons from 'lucide-vue-next'
import { Tooltip } from 'frappe-ui'

interface Link {
	label: string
	to?: RouteLocationRaw
	icon?: string
	count?: number
	activeFor?: string[]
	onlyMobile?: boolean
}

const {
	link,
	isCollapsed = false,
	showControls = false,
} = defineProps<{ link: Link; isCollapsed?: boolean; showControls?: boolean }>()

const emit = defineEmits(['openModal', 'deletePage'])

const route = useRoute()

const isActive = computed(() =>
	link?.activeFor?.includes(
		['Mailbox', 'Mail'].includes(route.name) ? route.params.mailbox : route.name,
	),
)

const openModal = (link: Link) => emit('openModal', link)

const deletePage = (link: Link) => emit('deletePage', link)
</script>
