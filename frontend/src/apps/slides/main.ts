import './index.css'

import { createApp } from 'vue'
import router from './router'
import App from './App.vue'

import { Button, FeatherIcon, setConfig, frappeRequest, resourcesPlugin } from 'frappe-ui'

import { session } from '@/stores/session'

let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)

app.use(router)
app.use(resourcesPlugin)

app.component('Button', Button)
app.component('FeatherIcon', FeatherIcon)
app.provide('session', session)
app.mount('#app')
