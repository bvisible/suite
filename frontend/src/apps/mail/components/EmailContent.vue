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
	const collapseButton = `
		<button
			style="
			background: ${colors.value.button};
			color: ${colors.value.text};
			padding: 0.5px 6px;
			border-radius: 4px;
			cursor: pointer;
			transition: background 0.2s;
			"
			onmouseover="this.style.background='${colors.value.buttonHover}'"
			onmouseout="this.style.background='${colors.value.button}'"
			onclick="this.nextElementSibling.classList.toggle('hidden');"
		>
			&middot;&middot;&middot;
		</button>
		<blockquote class="hidden">
	`

	const cleanedContent = content
		.replace(/<blockquote>/g, collapseButton)
		.replace(/<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>/g, '<b>&lt;$1&gt;</b>')

	/* eslint-disable no-useless-escape */
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<meta name="viewport" content="width=device-width, initial-scale=1">
			<meta name="color-scheme" content="${currentTheme.value}">
			<style>
				body {
					font-family: InterVar, ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
					font-size: 14px;
					line-height: 1.25rem;
				}

				body:not([style*="background"]) {
					color: ${colors.value.text} !important;
				}

				blockquote {
					margin: 8px 0;
					padding-left: 16px;
					border-left: 2px solid ${colors.value.button};
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

const colors = computed(() => THEMES[currentTheme.value as keyof typeof THEMES])

const THEMES = {
	light: {
		text: '#383838',
		button: '#F3F4F6',
		buttonHover: '#E5E7EB',
	},
	dark: {
		text: '#D4D4D4',
		button: '#374151',
		buttonHover: '#4B5563',
	},
}
</script>
