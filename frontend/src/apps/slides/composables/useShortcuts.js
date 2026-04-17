import { onMounted, onBeforeUnmount } from 'vue'
import { useEventListener } from '@vueuse/core'

import { useNavigationPanel } from '@/composables/useNavigationPanel'
import { commandHistory } from '@/stores/history'
import { useTextEditor } from '@/composables/useTextEditor'

import {
	slideIndex,
	changeSlide,
	saveSlide,
	selectionBounds,
	updateSelectionBounds,
	deleteSlide,
	changeEditorSlide,
	duplicateSlide,
	addEmptySlide,
} from '@/stores/slide'
import {
	focusElementId,
	resetFocus,
	addTextElement,
	selectAllElements,
	activeElementIds,
	activeElements,
	deleteElements,
	duplicateElements,
} from '@/stores/element'
import {
	changeSlideInSlideshow,
	startSlideShow,
	performNextStep,
	performPreviousStep,
} from '@/stores/slideshow'

import { isCmdOrCtrl } from '@/utils/helpers'

const { toggleNavigationPanel } = useNavigationPanel()
const { activeEditor, toggleMark } = useTextEditor()

export const useShortcuts = (inReadonlyMode, inSlideShowMode) => {
	let keydownListener

	const handleReadonlyModeShortcuts = (e) => {
		switch (e.key) {
			case 'ArrowUp':
				changeSlide(slideIndex.value - 1)
				break
			case 'ArrowDown':
				changeSlide(slideIndex.value + 1)
				break
			case 'b':
				if (isCmdOrCtrl(e)) toggleNavigationPanel(e)
				break
			case 'F5':
				e.preventDefault()
				startSlideShow()
				break
		}
	}

	const handleGlobalShortcuts = (e) => {
		if (isCmdOrCtrl(e) && e.code === 'KeyP') {
			e.preventDefault()
			startSlideShow()
			return
		}

		switch (e.key) {
			case 'Escape':
				resetFocus()
				break
			case 't':
				addTextElement()
				break
			case 'b':
				if (isCmdOrCtrl(e)) toggleNavigationPanel(e)
				break
			case 'a':
				if (isCmdOrCtrl(e)) selectAllElements(e)
				break
			case 's':
				if (isCmdOrCtrl(e)) saveSlide(e)
				break
			case 'Enter':
				addEmptySlide(e)
				break
			case 'F5':
				e.preventDefault()
				startSlideShow()
				break
		}
	}

	const handleArrowKeys = (key) => {
		let dx = 0
		let dy = 0

		if (key == 'ArrowLeft') dx = -1
		else if (key == 'ArrowRight') dx = 1
		else if (key == 'ArrowUp') dy = -1
		else if (key == 'ArrowDown') dy = 1

		updateSelectionBounds({
			left: selectionBounds.left + dx,
			top: selectionBounds.top + dy,
		})

		activeElements.value.forEach((element) => {
			element.left += dx
			element.top += dy
		})
	}

	const handleElementShortcuts = (e) => {
		switch (e.key) {
			case 'ArrowLeft':
			case 'ArrowRight':
			case 'ArrowUp':
			case 'ArrowDown':
				handleArrowKeys(e.key)
				break
			case 'Delete':
			case 'Backspace':
				deleteElements(e)
				break
			case 'd':
				if (isCmdOrCtrl(e)) duplicateElements(e, activeElements.value)
				break
			case 'b':
				if (activeEditor.value) toggleMark('bold')
				break
			case 'i':
				if (activeEditor.value) toggleMark('italic')
				break
			case 'u':
				if (activeEditor.value) toggleMark('underline')
				break
		}
	}

	const handleSlideShortcuts = (e) => {
		switch (e.key) {
			case 'ArrowUp':
				changeEditorSlide(slideIndex.value - 1)
				break
			case 'ArrowDown':
				changeEditorSlide(slideIndex.value + 1)
				break
			case 'Delete':
			case 'Backspace':
				deleteSlide()
				break
			case 'd':
				if (isCmdOrCtrl(e)) duplicateSlide(e)
				break
		}
	}

	const handleUndoRedo = (e) => {
		e.preventDefault()

		if (isCmdOrCtrl(e) && e.shiftKey && commandHistory.canRedo.value) {
			commandHistory.redo()
		} else if (isCmdOrCtrl(e) && !e.shiftKey && commandHistory.canUndo.value) {
			commandHistory.undo()
		}
	}

	const isUsingTiptapHistory = (e) => {
		if (e.key != 'z' || !activeEditor.value?.isEditable) return false

		const operation =
			isCmdOrCtrl(e) && e.shiftKey ? 'redo' : isCmdOrCtrl(e) && !e.shiftKey ? 'undo' : null
		if (!operation) return

		return activeEditor.value.can()[operation]()
	}

	const handleEditModeShortcuts = (e) => {
		const activeTag = document.activeElement.tagName
		const activeType = document.activeElement.type

		const useTiptapHistory = isUsingTiptapHistory(e)

		const editingText =
			(activeTag == 'INPUT' && activeType !== 'range') ||
			activeTag == 'TEXTAREA' ||
			useTiptapHistory

		if (editingText) return

		if (e.key == 'z') return handleUndoRedo(e)

		handleGlobalShortcuts(e)

		activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
	}

	const handleSlideShowModeShortcuts = (e) => {
		if (
			e.key == 'ArrowRight' ||
			e.key == 'ArrowDown' ||
			e.code == 'Space' ||
			e.key == 'PageDown'
		) {
			performNextStep()
		} else if (e.key == 'ArrowLeft' || e.key == 'ArrowUp' || e.key == 'PageUp') {
			performPreviousStep()
		} else if (e.key == 'F5') {
			e.preventDefault()
			changeSlideInSlideshow(0)
		}
	}

	const handleKeyDown = (e) => {
		if (inSlideShowMode.value) handleSlideShowModeShortcuts(e)
		else if (inReadonlyMode.value) handleReadonlyModeShortcuts(e)
		else handleEditModeShortcuts(e)
	}

	const cleanup = () => {
		keydownListener?.()
		keydownListener = null
	}

	onMounted(() => {
		cleanup()
		keydownListener = useEventListener(document, 'keydown', handleKeyDown)
	})

	onBeforeUnmount(() => {
		cleanup()
	})
}
