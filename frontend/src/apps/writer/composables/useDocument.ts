import { MaybeRefOrGetter, toValue } from 'vue'
import { useDoc } from 'frappe-ui/src/data-fetching'
import { DriveDocument } from '@/types/doctypes'
import { prettyData } from 'frappe-ui/frappe/drive/js/utils'

let docsCache: Record<string, ReturnType<typeof useDoc>> = {}

export default function useDocument(docId: MaybeRefOrGetter<string>) {
  interface Document extends DriveDocument {}

  interface DocumentMethods {
    addYjsUpdate: (params: { update_b64: string }) => void
    newVersion: (params: { data: string, title: string }) => void
  }

  let name = toValue(docId)
  if (!docsCache[name]) {
    docsCache[name] = useDoc<Document, DocumentMethods>({
      doctype: 'Drive File',
      url: '/api/method/writer.api.docs.get_document?file_id=' + docId,
      name: docId,
      transform: (doc) => {
        if (doc.settings) doc.settings = JSON.parse(doc.settings)
          if(doc.comments) doc.comments = doc.comments.map(k => ({...k, anchor: JSON.parse(k.anchor)}))
        return prettyData(doc)
      },
      methods: {
        addYjsUpdate: { name: 'add_yjs_update', skipOverride: true },
        newVersion: { name: 'new_version', skipOverride: true },
        addComment: { name: 'add_comment', skipOverride: true },
        saveToDisk: 'save_to_disk',
      },
    })
  }
  return docsCache[name] as ReturnType<typeof useDoc<Document, DocumentMethods>>
}
