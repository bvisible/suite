import { ref, onMounted, onUnmounted } from 'vue'

const activeEditor = ref(null)

export const useTextEditor = () => {
	const editorStyles = ref({
		textAlign: 'left',
		bold: false,
		italic: false,
		strike: false,
		underline: false,
		uppercase: false,
		fontSize: null,
		fontFamily: null,
		color: null,
		lineHeight: null,
		letterSpacing: null,
		opacity: null,
	})

	const update = () => {
		if (!activeEditor.value) return

		const editor = activeEditor.value
		const activeStyles = editor.getAttributes('textStyle')

		editorStyles.value = {
			bold: editor.isActive('bold'),
			italic: editor.isActive('italic'),
			strike: editor.isActive('strike'),
			underline: editor.isActive('underline'),
			bulletList: editor.isActive('bulletList'),
			orderedList: editor.isActive('orderedList'),
			uppercase: activeStyles.textTransform == 'uppercase',
			textAlign: editor.getAttributes('paragraph').textAlign || 'left',
			fontSize: parseInt(activeStyles.fontSize, 10) || null,
			fontFamily: activeStyles.fontFamily || null,
			color: activeStyles.color || null,
			lineHeight: activeStyles.lineHeight,
			letterSpacing: parseInt(activeStyles.letterSpacing, 10),
			opacity: parseInt(activeStyles.opacity, 10),
		}
	}

	const markCommands = {
		bold: 'toggleBold',
		italic: 'toggleItalic',
		strike: 'toggleStrike',
		underline: 'toggleUnderline',
	}

	const toggleCapitalize = (chain) => {
		const val = activeEditor.value.getAttributes('textStyle').textTransform
		const newVal = val == 'uppercase' ? null : 'uppercase'

		chain
			.setMark('textStyle', {
				textTransform: newVal,
			})
			.run()
	}

	const toggleMark = (property) => {
		const currentEditor = activeEditor.value

		const chain = currentEditor.chain().focus()

		const { empty } = currentEditor.state.selection
		if (empty) chain.selectAll()

		if (property == 'uppercase') return toggleCapitalize(chain)

		chain[markCommands[property]](property).run()
	}

	const setListProperty = (chain) => {
		if (editorStyles.value.bulletList) {
			chain.toggleBulletList().toggleOrderedList().run()
		} else if (editorStyles.value.orderedList) {
			chain.toggleOrderedList().run()
		} else {
			chain.toggleBulletList().run()
		}
	}

	const updateProperty = (property, value) => {
		const currentEditor = activeEditor.value

		const chain = currentEditor.chain().focus()

		if (property == 'list') return setListProperty(chain)

		const { empty } = currentEditor.state.selection
		if (empty) chain.selectAll()

		switch (property) {
			case 'textAlign':
				chain.setTextAlign(value).run()
				return
			case 'color':
				chain.setColor(value).run()
				return
			default:
				chain
					.setMark('textStyle', {
						[property]: value,
					})
					.run()
				return
		}
	}

	onMounted(() => {
		if (!activeEditor.value) return
		activeEditor.value.on('selectionUpdate', update)
		activeEditor.value.on('transaction', update)
		update()
	})

	onUnmounted(() => {
		if (!activeEditor.value) return
		activeEditor.value.off('selectionUpdate', update)
		activeEditor.value.off('transaction', update)
	})

	return {
		activeEditor,
		editorStyles,
		toggleMark,
		updateProperty,
	}
}
