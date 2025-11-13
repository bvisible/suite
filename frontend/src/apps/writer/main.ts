import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './index.css'
import store from './store'

import {
  setConfig,
  frappeRequest,
  FormControl,
  Button,
  focusDirective,
  pageMetaPlugin,
} from 'frappe-ui'
import { translation } from 'frappe-ui/frappe'
import { allUsers } from '@/resources/permissions'
const app = createApp(App)

setConfig('resourceFetcher', frappeRequest)
app.use(router)
app.use(store)
app.use(pageMetaPlugin)
app.directive('focus', focusDirective)
app.use(translation, 'drive.api.product.get_translations')
app.config.globalProperties.$user = (user) => {
  return allUsers.data?.find?.((k) => k.name === user)
}

app.component('FormControl', FormControl)
app.component('Button', Button)

app.mount('#app')
