import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { spritePlugin } from 'frappe-ui/experimental'

import App from '@/App.vue'
import router from '@/router'
import { configureFrappeUI } from '@/boot/config'
import { translationPlugin, loadTranslations } from '@/boot/translation' //// Neoffice — loadTranslations (#1316)
import { userResource, getSessionUser } from '@/boot/session'
import { initSentry } from '@/boot/sentry'

// One frappe-ui resource/session configuration for the whole suite.
configureFrappeUI()
if (getSessionUser()) {
  userResource.fetch()
}

//// Neoffice — the user's translations before the first render, for every app of the suite (#1316): Meet, Sheets
//// and Slides never loaded them, and a French account saw them in English.
await loadTranslations()

const app = createApp(App)

await initSentry(app, router)

app.use(createPinia())
app.use(router)
app.use(spritePlugin)
app.use(translationPlugin)

router.isReady().then(() => {
  app.mount('#app')
})
