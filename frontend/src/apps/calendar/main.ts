import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { frappeRequest, pageMetaPlugin, setConfig } from 'frappe-ui'

import App from '@/App.vue'
import router from '@/router'
import dayjs from '@/utils/dayjs'
import { userStore } from '@/stores/user'

import translationPlugin from './translation'

setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(router)
app.use(createPinia())
app.use(translationPlugin)
app.use(pageMetaPlugin)

const { userResource } = userStore()
app.provide('$user', userResource)
app.provide('$dayjs', dayjs)
app.mount('#app')
