import { createResource } from 'frappe-ui'

export const settings = createResource({
  url: '/api/method//api/method/drive.api.product.get_settings',
  method: 'GET',
  cache: 'settings',
})
