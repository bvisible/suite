<template>
	<div
		class="relative z-10 grid items-center justify-between border-b bg-white p-2"
		:class="$slots.default ? 'grid-cols-3' : 'grid-cols-2'"
		@wheel.prevent
	>
		<router-link
			v-if="!showNavbarDropdown"
			class="flex items-center gap-2"
			:to="{ name: 'Home' }"
		>
			<img src="/slides-logo.svg" class="h-7" />
			<div class="text-base font-semibold">Slides</div>
		</router-link>

		<Dropdown v-else :options="getContextMenuOptions()" :offset="16">
			<template #default>
				<div class="flex cursor-pointer items-center gap-2">
					<img src="/slides-logo.svg" class="h-7" />
					<div class="text-base font-semibold">Slides</div>
					<LucideChevronDown class="h-3 w-3 stroke-[1.5]" />
				</div>
			</template>
		</Dropdown>

		<slot></slot>

		<div class="flex items-center justify-end gap-2">
			<slot name="actions"></slot>
			<Button variant="solid" :label="primaryButton.label" @click="primaryButton.onClick">
				<template #prefix>
					<component :is="primaryButton.icon" size="14" class="stroke-[1.5] text-white" />
				</template>
			</Button>
		</div>
	</div>
</template>

<script setup>
import { h, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Dropdown, Button } from 'frappe-ui'
import { ChevronLeft, Palette, Plus } from 'lucide-vue-next'

const props = defineProps({
	showNavbarDropdown: {
		type: Boolean,
		default: false,
	},
	primaryButton: Object,
})

const emit = defineEmits(['performDropdownAction'])

const router = useRouter()

const getContextMenuOptions = () => {
	return [
		{
			group: '',
			items: [
				{
					label: 'Back to Home',
					icon: h(ChevronLeft, { class: 'stroke-[1.5] !size-3.5' }),
					onClick: () => {
						router.replace({
							name: 'Home',
						})
					},
				},
			],
		},
		{
			group: '',
			items: [
				{
					label: 'New Presentation',
					icon: h(Plus, { class: 'stroke-[1.5] !size-3.5 ms-0.5' }),
					onClick: () => {
						emit('performDropdownAction', 'create')
					},
				},
				{
					label: 'Change Theme',
					icon: h(Palette, { class: 'stroke-[1.5] !size-3.5 ms-0.5' }),
					onClick: () => {
						emit('performDropdownAction', 'update')
					},
				},
			],
		},
	]
}
</script>
