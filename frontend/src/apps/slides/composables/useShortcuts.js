import { watch, onActivated, onDeactivated } from 'vue'
import { useEventListener } from '@vueuse/core'
import { isDirty, syncThumbnail } from '@/stores/saving'

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

    const startSlideShow = () => {
        router.replace({
            name: 'Slideshow',
            params: router.currentRoute.value.params,
            query: router.currentRoute.value.query,
        })
    }

    const handleKeyDownForReadonly = (e) => {
        switch (e.key) {
            case 'F5':
                e.preventDefault()
                startSlideShow()
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
