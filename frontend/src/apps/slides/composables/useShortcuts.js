import { watch, onActivated, onDeactivated } from 'vue'
import { useEventListener } from '@vueuse/core'

import { useNavigationPanel } from '@/composables/useNavigationPanel'
import { useTextEditor } from '@/composables/useTextEditor'

import { slideIndex, changeSlide, saveSlide, selectionBounds, updateSelectionBounds, deleteSlide, changeEditorSlide, duplicateSlide } from '@/stores/slide'
import { focusElementId, resetFocus, addTextElement, selectAllElements, activeElementIds, activeElements, deleteElements, duplicateElements } from '@/stores/element'
import { startSlideShow } from '@/stores/slideshow'
import { isDirty, syncThumbnail } from '@/stores/saving'
import { isCmdOrCtrl } from '@/utils/helpers'

const { toggleNavigationPanel } = useNavigationPanel()
const { activeEditor, toggleMark } = useTextEditor()

export const useShortcuts = ({ readonlyMode }) => {
    let keydownListener
    let beforeUnloadListener

    // TODO: add this
    const handleBeforeUnload = (e) => {
        if (isDirty.value || syncThumbnail > 0) {
            e.preventDefault()
            e.returnValue = ''
        }
    }

    const handleReadonlyShortcuts = (e) => {
        switch (e.key) {
            case 'ArrowUp':
                changeSlide(slideIndex.value - 1)
                break
            case 'ArrowDown':
                changeSlide(slideIndex.value + 1)
                break
            case 'b':
                if (isCmdOrCtrl(e)) toggleNavigationPanel()
                break
            case 'F5':
                e.preventDefault()
                startSlideShow()
                break
        }
    }

    const handleUndoRedo = (e) => { }


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
                if (isCmdOrCtrl(e)) toggleNavigationPanel()
                break
            case 'a':
                if (isCmdOrCtrl(e)) selectAllElements(e)
                break
            case 's':
                if (isCmdOrCtrl(e)) saveSlide(e)
                break
            // case 'Enter':
            //     addEmptySlide(e)
            //     break
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

    const handleShortcuts = (e) => {
        const editingText =
            document.activeElement.getAttribute('contenteditable') ||
            document.activeElement.tagName == 'INPUT' ||
            focusElementId.value != null

        if (editingText) return

        if (e.key == 'z') return handleUndoRedo(e)

        handleGlobalShortcuts(e)

        activeElementIds.value.length ? handleElementShortcuts(e) : handleSlideShortcuts(e)
    }

    const handleKeyDown = (e) => {
        if (readonlyMode.value) handleReadonlyShortcuts(e)
        else handleShortcuts(e)
    }

    const cleanup = () => {
        keydownListener?.()
        beforeUnloadListener?.()
        keydownListener = null
        beforeUnloadListener = null
    }

    onActivated(() => {
        cleanup()
        keydownListener = useEventListener(document, 'keydown', handleKeyDown)
    })

    onDeactivated(() => {
        cleanup()
    })
}
