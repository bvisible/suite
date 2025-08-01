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

const { activeTheme } = useTheme()

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
			margin: 12px 0;
			"
			onmouseover="this.style.background='${colors.value.buttonHover}'"
			onmouseout="this.style.background='${colors.value.button}'"
			onclick="this.nextElementSibling.classList.toggle('quote-hidden');"
		>
			&middot;&middot;&middot;
		</button>
	`

	const transformedContent = content
		.replace(
			/<div\s+class="(gmail_quote|frappe_mail_quote)"([^>]*)>([\s\S]*?)<\/div>/gi,
			(_, quoteClass, otherAttrs, innerHtml) =>
				`${collapseButton}<div class="quote-hidden ${quoteClass}"${otherAttrs}>${innerHtml}</div>`,
		)
		.replace(/<([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>/g, '<b>&lt;$1&gt;</b>')

	/* eslint-disable no-useless-escape */
	return `
		<!DOCTYPE html>
		<html>
		<head>
			<meta name="viewport" content="width=device-width, initial-scale=1">
			<meta name="color-scheme" content="${activeTheme.value}">
			<style>
				body {
					font-family: InterVar, ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
					font-size: 14px;
					line-height: 1.25rem;
				}

				blockquote {
					margin: 8px 0;
					padding-left: 12px;
					border-left: 1px solid ${colors.value.buttonHover};
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

				.quote-hidden {
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
			${transformedContent}
			<script>
				document.addEventListener('click', (e) => {
					if (e.target.tagName === 'A') {
						e.preventDefault();
						window.open(e.target.href, '_blank');
					}
				});
				${colors.value.script}
			<\/script>
		</body>
		</html>
	`
})

const colors = computed(() => THEME_CONFIG[activeTheme.value])

const THEME_CONFIG = {
	light: {
		text: '#383838',
		button: '#F3F4F6',
		buttonHover: '#E5E7EB',
		script: '',
	},
	dark: {
		text: '#D4D4D4',
		button: '#374151',
		buttonHover: '#4B5563',
		script: `
			function hasBackground(el) {
				while (el && el !== document.body) {
					const bg = getComputedStyle(el).backgroundColor;
					if (bg !== 'transparent' && bg !== 'rgba(0, 0, 0, 0)') {
						return true;
					}
					el = el.parentElement;
				}
				return false;
			}

			function walkAndWrapTextNodes(node) {
				for (let child of Array.from(node.childNodes)) {
					if (child.nodeType === 3) {
						const trimmed = child.textContent.trim();
						if (
							trimmed.length > 0 &&
							!hasBackground(child.parentElement) &&
							child.parentElement.tagName !== 'A'
						) {
							child.parentElement.style.setProperty('color', '#D4D4D4');
						}
					} else if (child.nodeType === 1) {
						walkAndWrapTextNodes(child);
					}
				}
			}

			walkAndWrapTextNodes(document.body);
		`,
	},
}
</script>
