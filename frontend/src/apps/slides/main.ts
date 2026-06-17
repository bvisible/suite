import './index.css'

import { createApp } from 'vue'
import { router } from './router'
import App from './App.vue'

import { Button, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

import { session } from '@/stores/session'

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)

const isDriveInstalled = window.apps?.includes('drive') ?? false

app.component('Button', Button)
app.provide('session', session)
app.provide('isDriveInstalled', isDriveInstalled)
app.mount('#app')

// Register Service Worker for Prod Environment
// intentional to avoid caching + HMR conflict issues during dev
if ('serviceWorker' in navigator && import.meta.env.PROD) {
    // service worker is served from root so that
    // "/private/files/" can be intercepted correctly
    navigator.serviceWorker.register('/service-worker.js').catch((err) => {
        console.warn('Service Worker Registration Failed:', err)
    })
}
