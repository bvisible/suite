import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './index.css'
import store from "./store"

import {
  setConfig,
  frappeRequest,
  FormControl,
  Button
} from "frappe-ui"
import {translation} from 'frappe-ui/frappe'
const app = createApp(App)

setConfig('resourceFetcher', frappeRequest)
app.use(router)
app.use(store)
app.use(translation, "drive.api.product.get_translations")


app.component("FormControl", FormControl)
app.component("Button", Button)

app.mount('#app')
