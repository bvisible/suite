import { useList, createResource, useCall } from 'frappe-ui'
import { prettyData } from '@/utils'

export const getDocuments = useList({
  url: '/api/method/writer.api.general.get_document_list',
  start: 0,
  limit: 50,
  immediate: false,
  cacheKey: 'writer-document-list',
  transform: (data) => {
    return prettyData(data)
  },
})

export const createDocument = createResource({
  method: 'POST',
  url: 'writer.api.docs.create_document_entity',
  makeParams: (params) => params,
})

export const getTemplates = useList({
  doctype: 'Writer Template',
  fields: ['name', 'title', 'content', 'keymap'],
  cacheKey: 'writer-templates',
  immediate: true,
})

export const search = createResource({
  url: '/api/method/writer.api.general.search',
  method: 'GET',
  makeParams: (params) => {
    console.log('PARAMSS', params)
    return params
  },
})
