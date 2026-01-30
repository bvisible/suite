import { watch, onActivated, onDeactivated } from 'vue'
import { useEventListener } from '@vueuse/core'

import { useNavigationPanel } from '@/composables/useNavigationPanel'

import { slideIndex, changeSlide } from '@/stores/slide'
import { focusElementId } from '@/stores/element'
import { startSlideShow } from '@/stores/slideshow'
import { isDirty, syncThumbnail } from '@/stores/saving'
import { isCmdOrCtrl } from '@/utils/helpers'

const { toggleNavigationPanel } = useNavigationPanel()

export const useShortcuts = ({ readonlyMode, router }) => {
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
                changeSlide(router, slideIndex.value - 1)
                break
            case 'ArrowDown':
                changeSlide(router, slideIndex.value + 1)
                break
            case 'b':
                if (isCmdOrCtrl(e)) toggleNavigationPanel()
                break
            case 'F5':
                e.preventDefault()
                startSlideShow(router)
                break
        }
    }

    const handleUndoRedo = (e) => { }

    const handleShortcuts = (e) => {
        const editingText =
            document.activeElement.getAttribute('contenteditable') ||
            document.activeElement.tagName == 'INPUT' ||
            focusElementId.value != null

        if (editingText) return

        if (e.key == 'z') return handleUndoRedo(e)
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
