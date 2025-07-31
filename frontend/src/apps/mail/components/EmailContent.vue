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

import { useTheme } from '@/utils/composables'

const { content } = defineProps<{ content: string }>()

const { currentTheme } = useTheme()

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
			<meta name="color-scheme" content=${currentTheme.value}>
			<style>
				body {
					font-family: InterVar, ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
					font-size: 14px;
					line-height: 1.25rem;
				}

				body:not([style*="background"]) {
					color: ${currentTheme.value === 'light' ? '#383838' : '#D4D4D4'} !important;
				}

				blockquote {
					margin: 8px 0;
					padding-left: 16px;
					border-left: 2px solid ${currentTheme.value === 'dark' ? '#4B5563' : '#E5E7EB'};
				}

				table {
					color: inherit !important;
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

				.email-pixel {
					display: none !important;
					visibility: hidden !important;
					width: 0 !important;
					height: 0 !important;
					overflow: hidden !important;
				}

				@media (max-width: 640px) {
                    /* Only override specific problematic patterns */
                    table[width="600"], table[width="600px"] {
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
