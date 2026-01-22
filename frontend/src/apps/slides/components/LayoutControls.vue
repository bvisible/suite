<template>
	<div class="flex flex-col p-3 pt-0">
		<div class="sticky top-0 z-10 bg-white py-3">
			<TabButtons
				:buttons="[
					{ label: 'Themes', value: 'themes' },
					{ label: 'Layouts', value: 'layouts' },
				]"
				v-model="selectedTab"
				class="tab-buttons"
			/>
		</div>
		<div class="flex flex-col gap-3 overflow-y-auto">
			<div
				v-if="selectedTab === 'themes'"
				class="aspect-video rounded border"
				v-for="template in templateList"
				:style="getThumbnailCardStyles(template.layouts[0].thumbnail)"
			></div>
		</div>
	</div>
</template>

<script setup>
import { ref, inject } from 'vue'
import { TabButtons } from 'frappe-ui'
import { getThumbnailCardStyles } from '@/utils/helpers'
import { templateList } from '@/stores/presentation'

const selectedTab = ref('themes')
</script>

<style>
.tab-buttons div,
.tab-buttons button {
	width: 100%;
	flex: 1;
}
</style>
