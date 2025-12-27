import { MaybeRefOrGetter, toValue } from 'vue'
import { useDoc } from 'frappe-ui/src/data-fetching'
import { DriveDocument } from '@/types/doctypes'
import { prettyData } from 'frappe-ui/frappe/drive/js/utils'
import { getDocuments } from '@/resources/'

export default function useDocument(docId: MaybeRefOrGetter<string>) {
  interface Document extends DriveDocument {}

  interface DocumentMethods {
    addYjsUpdate: (params: { update_b64: string }) => void
    newVersion: (params: { data: string; title: string }) => void
  }

  const doc = useDoc<Document, DocumentMethods>({
    doctype: 'Drive File',
    url: '/api/method/writer.api.docs.get_document?file_id=' + docId,
    name: docId,
    transform: (doc) => {
      if (doc.settings) doc.settings = JSON.parse(doc.settings)
      if (doc.comments)
        doc.comments = doc.comments.map((k) => ({
          ...k,
          anchor: JSON.parse(k.anchor),
        }))
      return prettyData(doc)
    },
    methods: {
      addYjsUpdate: { name: 'add_yjs_update', skipOverride: true },
      newVersion: { name: 'new_version', skipOverride: true },
      saveDoc: { name: 'save_doc', skipOverride: true },
      saveComments: { name: 'save_comments', skipOverride: true },
      saveHtml: { name: 'save_html', skipOverride: true },
      toggleFav: { name: 'toggle_favourite', skipOverride: true },
      updateSettings: { name: 'update_settings', skipOverride: true },
      saveToDisk: 'save_to_disk',
    },
  })
  doc.onSuccess(() => {
    getDocuments.updateRow({
      name: docId,
      accessed: new Date().toISOString(), // or just new Date() depending on your backend
    })
  })
  return doc
}
