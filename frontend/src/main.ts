import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { spritePlugin } from 'frappe-ui/experimental'

import App from '@/App.vue'
import router from '@/router'
import { configureFrappeUI } from '@/boot/config'
import { translationPlugin } from '@/boot/translation'
// //// Neoffice — dates in the reader's language (boot/dateLocale.ts, #1316).
import { setDateLocale } from '@/boot/dateLocale'
import { userResource, getSessionUser } from '@/boot/session'
import { initSentry } from '@/boot/sentry'

// //// Neoffice — before anything formats a date: dayjs reads English until told otherwise (#1316).
setDateLocale()

// One frappe-ui resource/session configuration for the whole suite.
configureFrappeUI()
if (getSessionUser()) {
  userResource.fetch()
}

const app = createApp(App)

//// Neoffice — before the router: it copies a route's `meta` when it is installed, and the titles that the build says
//// through __() (neoffice-i18n, #1592) read `window.__`, which this plugin sets: after the router, the whole Suite was
//// blank on 15.10 (« __ is not defined » at install). Identity until the catalogue is loaded, as before.
app.use(translationPlugin)

await initSentry(app, router)

app.use(createPinia())
app.use(router)
app.use(spritePlugin)
//// Neoffice — translationPlugin is installed above, before the router (a title read at install needs window.__).

router.isReady().then(() => {
  app.mount('#app')
})
