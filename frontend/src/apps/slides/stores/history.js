import { ref, reactive, nextTick } from 'vue'
import { watchIgnorable, useManualRefHistory } from '@vueuse/core'

import { slidesLength } from '@/stores/presentation'
import { slides, currentSlide, slideIndex, changeEditorSlide, updateThumbnail } from '@/stores/slide'
import { activeElementIds } from '@/stores/element'
import { activeEditor } from '@/composables/useTextEditor'
import { isCmdOrCtrl, cloneObj } from '@/utils/helpers'

let historyControl = null

const historyState = ref({
    elementIds: '',
    activeSlide: '',
    slides: [],
})

const historyMetadata = reactive({})

const updateHistoryState = (slides, activeSlide, elementIds) => {
    const slidesClone = [...slides].map((slide, idx) => {
        return {
            ...slide,
            elements: slide.elements.map((el) => cloneObj(el)),
        }
    })

    historyState.value = {
        elementIds: elementIds,
        activeSlide: activeSlide,
        slides: slidesClone,
    }
}

let ignoreUpdates = null

const commitToHistory = (state) => {
    const activeSlide = currentSlide.value?.name
    const elementIds = activeElementIds.value

    updateHistoryState(state, activeSlide, elementIds)

    historyControl?.commit()
}

const initHistory = () => {
    historyState.value.activeSlide = currentSlide.value?.name
    historyControl = useManualRefHistory(historyState, {
        capacity: 25,
        clone: true,
        deep: true,
    })

    const watchObj = watchIgnorable(
        () => slides.value,
        (newVal) => {
            if (!newVal.length) return
            commitToHistory(newVal)
        },
        { deep: true },
    )

    ignoreUpdates = watchObj.ignoreUpdates
}

const recentlyRestored = ref(false)

const getRestoredSlideId = (oldList, newList) => {
    let restoredId = ''
    newList.forEach((slide, index) => {
        if (!oldList.find((s) => s.name === slide.name)) {
            restoredId = index
        }
    })
    return restoredId
}

const getPrevToDeletedSlideId = (oldList, newList) => {
    let prevId = null
    oldList.forEach((slide, index) => {
        if (!newList.find((s) => s.name === slide.name)) {
            prevId = index - 1
        }
    })
    return prevId
}

const wereSlidesReordered = (oldList, newList) => {
    if (oldList.length !== newList.length) return false

    for (let i = 0; i < newList.length; i++) {
        if (oldList[i] && oldList[i].name !== newList[i].name) {
            return true
        }
    }
    return false
}

const getJumpToSlideId = (operation, oldList, newList) => {
    // reordered slides -> the jump to index becomes the slide that was moved
    const didReorder = wereSlidesReordered(oldList, newList)
    if (didReorder && operation == 'undo') return historyMetadata.focusIndexPostUndo
    if (didReorder && operation == 'redo') return historyMetadata.focusIndexPostRedo

    if (oldList.length < newList.length) {
        return getRestoredSlideId(oldList, newList)
    }

    if (oldList.length > newList.length) {
        return getPrevToDeletedSlideId(oldList, newList)
    }

    if (historyControl.undoStack.value.length == 1 && operation == 'undo') {
        return Math.max(0, Math.min(slideIndex.value, slidesLength.value - 1))
    }

    const slideId = historyState.value.activeSlide
    return slides.value.findIndex((slide) => slide.name === slideId)
}

const restoreState = (state, jumpToSlideId) => {
    ignoreUpdates(() => {
        slides.value = JSON.parse(JSON.stringify(state)).map((slide, idx) => {
            if (idx === jumpToSlideId) {
                slide.thumbnail = ''
            }
            return slide
        })
        slidesLength.value = slides.value.length
    })
}

const jumpToSlide = async (operation, oldList, newList) => {
    const jumpToSlideId = getJumpToSlideId(operation, oldList, newList)
    const onActiveSlide = jumpToSlideId == slideIndex.value

    if (!onActiveSlide && jumpToSlideId != null) {
        await changeEditorSlide(jumpToSlideId, false)

        recentlyRestored.value = true
        setTimeout(() => {
            recentlyRestored.value = false
        }, 1000)
    }

    return jumpToSlideId
}

const jumpToActiveElements = () => {
    const elementsToFocus = [...historyState.value.elementIds]

    if (activeElementIds.value != elementsToFocus) {
        activeElementIds.value = elementsToFocus
    }
}

const handleHistoryOperation = async (operation) => {
    activeElementIds.value = []

    if (operation == 'undo') await historyControl.undo()
    else if (operation == 'redo') await historyControl.redo()

    const oldList = JSON.parse(JSON.stringify(slides.value))
    const newList = JSON.parse(JSON.stringify(historyState.value.slides))

    const jumpToSlideId = await jumpToSlide(operation, oldList, newList)

    restoreState(historyState.value.slides, jumpToSlideId)

    await nextTick()

    updateThumbnail(jumpToSlideId)

    nextTick(() => {
        jumpToActiveElements()
    })
}

const handleUndoRedo = (e) => {
    e.preventDefault()

    if (activeEditor.value?.isEditable) {
        e.stopPropagation()
        return
    }

    if (isCmdOrCtrl(e) && e.shiftKey && historyControl.canRedo.value) {
        handleHistoryOperation('redo')
    } else if (isCmdOrCtrl(e) && historyControl.undoStack.value.length > 1) {
        handleHistoryOperation('undo')
    }
}

export {
    recentlyRestored,
    historyMetadata,
    ignoreUpdates,
    initHistory,
    handleUndoRedo
}
