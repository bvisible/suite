import { ref, computed } from 'vue'
import { presentationId } from '@/stores/presentation'
import { focusedSlide, slideIndex, slides } from '@/stores/slide'

const inSlideShow = ref(false)

const startSlideShow = (router) => {
    router.replace({
        name: 'Slideshow',
        params: { presentationId: presentationId.value },
        query: { slide: slideIndex.value + 1 }
    })
}

const endSlideShow = (router) => {
    inSlideShow.value = false
    const slide =
        slideIndex.value == slides.value.length ? slides.value.length : slideIndex.value + 1
    router.replace({
        name: 'PresentationEditor',
        params: { presentationId: presentationId.value },
        query: { slide: slide },
    })
}

const showSlideshowEndScreen = computed(() => {
    return slideIndex.value >= slides.value.length
})

export {
    inSlideShow,
    showSlideshowEndScreen,
    startSlideShow,
    endSlideShow,
}