import { ref } from 'vue'
import { activeElementIds, activeElement } from '@/stores/element'

const isNavigationPanelOpen = ref(true)

const toggleNavigationPanel = () => {
    if (!activeElementIds.value.length || activeElement.value.type != 'text') {
        isNavigationPanelOpen.value = !isNavigationPanelOpen.value
    }
}

export const useNavigationPanel = () => {
    return {
        isNavigationPanelOpen,
        toggleNavigationPanel,
    }
}