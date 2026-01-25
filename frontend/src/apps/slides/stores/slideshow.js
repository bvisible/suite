import { ref, computed } from 'vue'
import { focusedSlide, slideIndex, slides, setSlideIndex } from '@/stores/slide'

const inSlideShow = ref(false)

const startSlideShow = (router) => {
    router.replace({
        name: 'Slideshow',
        params: router.currentRoute.value.params,
        query: { slide: slideIndex.value + 1 }
    })
}

const endSlideShow = (router) => {
    inSlideShow.value = false
    focusedSlide.value = null
    const slide =
        slideIndex.value == slides.value.length ? slides.value.length : slideIndex.value + 1
    setSlideIndex(slide)
    router.replace({
        name: 'PresentationEditor',
        params: router.currentRoute.value.params,
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