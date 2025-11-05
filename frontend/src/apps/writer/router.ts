import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/writer'),
  routes: [
    {
      path: '/',
      name: 'Documents',
      component: () => import('@/pages/Documents.vue'),
    },
    {
      path: '/w/:entityName/:slug?',
      name: 'Document',
      meta: { documentPage: true, allowGuest: true },
      component: () => import('@/pages/Document.vue'),
      props: true,
    },
  ],
})

export default router
