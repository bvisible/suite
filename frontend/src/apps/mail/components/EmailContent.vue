<template>
	<div v-if="!isIframeReady" class="animate-pulse space-y-2 py-4">
		<div
			v-for="i in 5"
			:key="i"
			class="bg-surface-gray-3 h-2"
			:style="{ width: `${Math.floor(Math.random() * 40) + 60}%` }"
		/>
	</div>
	<IframeResizer
		v-show="isIframeReady"
		class="w-full"
		license="GPLv3"
		:scrolling="true"
		:srcdoc
		@on-ready="isIframeReady = true"
	/>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
// eslint-disable-next-line import/no-unresolved
import IframeResizer from '@iframe-resizer/vue/sfc'

const { content } = defineProps<{ content: string }>()

const isIframeReady = ref(false)

const srcdoc = computed(() => {
	const cleanedContent = content
		.replace(
			/<blockquote>/g,
			'<button onclick="this.nextElementSibling.classList.toggle(\'hidden\');">...</button><blockquote class="hidden">',
		)
		.replace(/<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>/g, '<b>&lt;$1&gt;</b>')

	/* eslint-disable no-useless-escape */
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<meta name="viewport" content="width=device-width, initial-scale=1">
			<style>
				body {
					font-family: InterVar, ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
					font-size: 14px;
					line-height: 1.25rem;
				}

				blockquote {
					margin: 8px 0;
					padding-left: 16px;
					border-left: 2px solid #e5e7eb;
				}

				button {
					background: none;
					border: none;
					cursor: pointer;
					padding: 0;
				}

				.hidden {
					display: none;
				}

				@media (max-width: 640px) {
					/* Force override any remaining fixed widths */
					table[style*="width"] {
						width: 100% !important;
					}
				}
			</style>
			<script
			src="https://cdn.jsdelivr.net/npm/@iframe-resizer/child@5.4.6"
			type="text/javascript"
			><\/script>
		</head>
		<body>
			${cleanedContent}
			<script>
				document.addEventListener('click', (e) => {
					if (e.target.tagName === 'A') {
						e.preventDefault();
						window.open(e.target.href, '_blank');
					}
				});
			<\/script>
		</body>
		</html>
	`
})
</script>
