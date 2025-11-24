import { createRouter, createWebHistory } from 'vue-router'
import store from './store'

const router = createRouter({
  history: createWebHistory('/writer'),
  routes: [
    {
      path: '/',
      name: 'Home',
      component: () => import('@/pages/Documents.vue'),
      beforeEnter: () => {
        if (!store.getters.isLoggedIn) return '/login'
      },
    },
    {
      path: '/w/:id/:slug?',
      name: 'Document',
      meta: { documentPage: true, allowGuest: true },
      component: () => import('@/pages/Document.vue'),
      props: true,
    },
  ],
})

export default router
