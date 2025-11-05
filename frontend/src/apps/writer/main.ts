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
const app = createApp(App)

setConfig('resourceFetcher', frappeRequest)
app.use(router)
app.use(store)

app.component("FormControl", FormControl)
app.component("Button", Button)

app.mount('#app')
