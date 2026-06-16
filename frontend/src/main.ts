import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { spritePlugin } from 'frappe-ui/icons'
import { pageMetaPlugin } from 'frappe-ui'

import App from '@/App.vue'
import router from '@/router'
import { configureFrappeUI } from '@/boot/config'

// One frappe-ui resource/session configuration for the whole suite.
configureFrappeUI()

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(pageMetaPlugin)
app.use(spritePlugin)

router.isReady().then(() => {
  app.mount('#app')
})
