<template>
	<div ref="textRef" v-html="textHTML"></div>
</template>
<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
	content: {
		type: String,
		required: true,
	},
})

const textRef = ref(null)

const encodeCharForHtml = (c) => {
	if (c === ' ') return '&nbsp;'
	if (c === '&') return '&amp;'
	if (c === '<') return '&lt;'
	if (c === '>') return '&gt;'
	return c
}

const findSpanAncestor = (node, root) => {
	let el = node.parentElement
	while (el && el !== root) {
		if (el.tagName && el.tagName.toLowerCase() === 'span') return el
		el = el.parentElement
	}
	return null
}

const getWrapsForChar = (txt, span) => {
	const inlineTags = new Set(['strong', 'b', 'u', 'i', 'em', 's'])

	let openWrap = ''
	let closeWrap = ''
	let el = txt.parentElement
	while (el && el !== span) {
		const tag = el.tagName && el.tagName.toLowerCase()
		if (inlineTags.has(tag)) {
			openWrap = `<${tag}>` + openWrap
			closeWrap = closeWrap + `</${tag}>`
		}
		el = el.parentElement
	}

	return { openWrap, closeWrap }
}

const createSpansForTextNode = (blockNode, textNode) => {
	let spansHTML = ''

	const span = findSpanAncestor(textNode, blockNode)
	const style = span?.getAttribute('style') || ''

	const { openWrap, closeWrap } = getWrapsForChar(textNode, span)

	for (const ch of textNode.nodeValue) {
		spansHTML += `<span style="${style}">${openWrap}${encodeCharForHtml(ch)}${closeWrap}</span>`
	}

	return spansHTML
}

const getNewChildrenHTML = (blockNode) => {
	let childrenHTML = ''

	const walker = document.createTreeWalker(blockNode, NodeFilter.SHOW_TEXT)
	while (walker.nextNode()) {
		const splitSpansHTML = createSpansForTextNode(blockNode, walker.currentNode)
		childrenHTML += splitSpansHTML
	}

	return childrenHTML
}

const getHTMLForContent = (content = props.content) => {
	const parser = new DOMParser()
	const doc = parser.parseFromString(content, 'text/html')

	const walker = doc.createTreeWalker(
		doc.body,
		typeof NodeFilter !== 'undefined' ? NodeFilter.SHOW_ELEMENT : 1,
		null,
		false,
	)
	while (walker.nextNode()) {
		const node = walker.currentNode
		if (['P', 'LI'].includes(node.tagName)) {
			const nodeCopy = node.cloneNode(true)
			node.innerHTML = getNewChildrenHTML(nodeCopy)
		}
	}

	return doc.body.innerHTML
}

const textHTML = ref(getHTMLForContent())
</script>
