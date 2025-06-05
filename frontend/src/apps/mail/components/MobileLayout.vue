<template>
	<div class="flex h-full flex-col">
		<div id="scrollContainer" class="h-full pb-10">
			<slot />
		</div>
		<div
			v-if="tabs"
			class="standalone:pb-4 fixed bottom-0 flex w-full justify-around border-t border-gray-300 bg-white"
			:style="{
				gridTemplateColumns: `repeat(${tabs.length}, minmax(0, 1fr))`,
			}"
		>
			<button
				v-for="tab in tabs"
				:key="tab.label"
				class="flex flex-col items-center justify-center py-3 transition active:scale-95"
				@click="router.push(tab.to)"
			>
				<component
					:is="icons[tab.icon]"
					class="stroke-1.5 h-6 w-6"
					:class="[isActive(tab) ? 'text-gray-900' : 'text-gray-600']"
				/>
			</button>
		</div>
	</div>
</template>
<script setup lang="ts">
import { useRouter } from 'vue-router'
import * as icons from 'lucide-vue-next'

const router = useRouter()

const tabs = []

const isActive = (tab) => tab.activeFor?.includes(router.currentRoute.value.name)
</script>
