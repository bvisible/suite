<!-- //// Neoffice: global Frappe search for SPA surfaces that don't have their
     own search (Calendar / Meet / Mail / …). The cockpit search bar triggers
     this (fallback onSearch in NeoCockpitBridge). Calls the SAME endpoint as
     the desk awesome bar (frappe.utils.global_search.search) and navigates to
     the doc in the desk. Drive keeps its own SearchPopup instead. //// -->
<template>
	<Dialog v-model="show" :options="{ size: '2xl' }">
		<template #body>
			<div class="p-2">
				<div class="flex items-center gap-2 border-b border-outline-gray-2 px-2 pb-3">
					<svg class="size-5 text-ink-gray-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
					</svg>
					<input
						ref="input"
						v-model="query"
						class="w-full bg-transparent text-lg text-ink-gray-9 outline-none placeholder:text-ink-gray-4"
						:placeholder="__('Search everywhere…')"
						@keydown.enter="openFirst"
						@keydown.esc="show = false"
					/>
				</div>

				<div class="max-h-[55vh] overflow-y-auto py-2">
					<div v-if="results.loading" class="px-3 py-6 text-center text-sm text-ink-gray-5">
						{{ __('Searching…') }}
					</div>
					<div
						v-else-if="query.trim() && !items.length"
						class="px-3 py-6 text-center text-sm text-ink-gray-5"
					>
						{{ __('No results for “{0}”.', [query.trim()]) }}
					</div>
					<div v-else-if="!query.trim()" class="px-3 py-6 text-center text-sm text-ink-gray-4">
						{{ __('Search across all your documents.') }}
					</div>
					<ul v-else>
						<li
							v-for="(r, i) in items"
							:key="i"
							class="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 hover:bg-surface-gray-2"
							@click="openResult(r)"
						>
							<span
								class="shrink-0 rounded bg-surface-gray-3 px-1.5 py-0.5 text-xs font-medium text-ink-gray-7"
							>
								{{ __(r.doctype) }}
							</span>
							<span class="min-w-0 flex-1">
								<span class="block truncate text-sm font-medium text-ink-gray-9">{{ r.name }}</span>
								<span v-if="snippet(r.content)" class="block truncate text-xs text-ink-gray-5">
									{{ snippet(r.content) }}
								</span>
							</span>
						</li>
					</ul>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { Dialog, createResource } from 'frappe-ui'

const show = defineModel({ default: false })

const query = ref('')
const input = ref(null)

const results = createResource({
	url: 'frappe.utils.global_search.search',
	makeParams: () => ({ text: query.value.trim(), limit: 20 }),
	debounce: 300,
})

const items = computed(() => (Array.isArray(results.data) ? results.data : []))

watch(query, (q) => {
	if (q.trim()) results.submit()
	else results.data = []
})

// Focus the field whenever the dialog opens.
watch(
	show,
	(open) => {
		if (!open) {
			query.value = ''
			results.data = []
			return
		}
		nextTick(() => input.value?.focus())
	},
	{ immediate: true },
)

function snippet(content) {
	if (!content) return ''
	// global_search stores "Label: value ||| Label: value" — clean + trim
	return content.replace(/\s*\|\|\|\s*/g, ' · ').replace(/\s+/g, ' ').trim().slice(0, 120)
}

function openResult(r) {
	if (!r?.doctype || !r?.name) return
	const slug = r.doctype.toLowerCase().replace(/ /g, '-')
	// Global-search hits are ERP docs living in the desk — full load to /app.
	window.location.href = `/app/${slug}/${encodeURIComponent(r.name)}`
	show.value = false
}

function openFirst() {
	if (items.value.length) openResult(items.value[0])
}
</script>
