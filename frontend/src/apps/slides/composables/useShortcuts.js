import { watch, onActivated, onDeactivated } from 'vue'
import { useEventListener } from '@vueuse/core'

import { useNavigationPanel } from '@/composables/useNavigationPanel'

import { slideIndex, changeSlide } from '@/stores/slide'
import { startSlideShow } from '@/stores/slideshow'
import { isDirty, syncThumbnail } from '@/stores/saving'
import { isCmdOrCtrl } from '@/utils/helpers'

const { toggleNavigationPanel } = useNavigationPanel()

export const useShortcuts = ({ readonlyMode, router }) => {
    let keydownListener
    let beforeUnloadListener

    const handleKeyDown = (e) => {
    }

    const handleBeforeUnload = (e) => {
        if (isDirty.value || syncThumbnail > 0) {
            e.preventDefault()
            e.returnValue = ''
        }
    }

    const handleKeyDownForReadonly = (e) => {
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

    const bindReadonly = () => {
        keydownListener = useEventListener(document, 'keydown', handleKeyDownForReadonly)
    }

    const bindEditable = () => {
        keydownListener = useEventListener(document, 'keydown', handleKeyDown)
        beforeUnloadListener = useEventListener(window, 'beforeunload', handleBeforeUnload)
    }

    const cleanup = () => {
        keydownListener?.()
        beforeUnloadListener?.()
        keydownListener = null
        beforeUnloadListener = null
    }

    onActivated(() => {
        cleanup()
        readonlyMode.value ? bindReadonly() : bindEditable()
    })

    onDeactivated(() => {
        cleanup()
    })

    watch(readonlyMode, () => {
        cleanup()
        readonlyMode.value ? bindReadonly() : bindEditable()
    })
}
