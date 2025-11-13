import * as Y from 'yjs'
import { IndexeddbPersistence } from 'y-indexeddb'
import { WebrtcProvider } from 'y-webrtc'
import { toUint8Array, fromUint8Array } from 'js-base64'
import { debounce, toast } from 'frappe-ui'

import store from '@/store'

export function useYjs(document, edited) {
  const doc = new Y.Doc({ gc: false })
  Y.applyUpdate(
    doc,
    Y.mergeUpdates([
      toUint8Array(document.doc.content || 'AAA='),
      ...document.doc.updates.map(({ data }) => toUint8Array(data)),
    ]),
  )
  let serverStateVector = Y.encodeStateVector(doc)
  const indexeddb = new IndexeddbPersistence('wdoc-' + document.doc.name, doc)

  // Saving to server
  const save = async (manual = false) => {
    if (!manual && !edited.value) return
    // Compute a diff relative to server’s last known state
    const incrementalDiff = Y.encodeStateAsUpdate(doc, serverStateVector)
    const updateB64 = fromUint8Array(incrementalDiff)
    try {
      const data = await document.addYjsUpdate.submit({
        update_b64: updateB64,
      })
      if (data?.success) {
        serverStateVector = Y.encodeStateVector(doc)
      } else if (data?.skipped) {
        console.log(
          'Server skipped update - probably because other people are collaborating',
        )
      }
    } catch (error) {
      console.error('Failed to save YJS update:', error)
      toast.error('Could not save document.')
    }
  }
  const autosave = debounce(save, 2000)

  // WebRTC for real-time P2P collaboration
  const provider = new WebrtcProvider('wdoc-' + document.name, doc, {
    signaling: ['wss://signal.frappe.cloud'],
    peerOpts: {
      config: {
        iceServers: [
          { urls: 'stun:stun.l.google.com:19302' },
          {
            urls: [
              'turn:signal.frappe.cloud:3478?transport=udp',
              'turn:signal.frappe.cloud:3478?transport=tcp',
            ],
            username: 'turnuser',
            credential: 'turnpass',
          },
        ],
      },
    },
  })

  const permanentUserData = new Y.PermanentUserData(doc)
  permanentUserData.setUserMapping(doc, doc.clientID, store.state.user.id)

  doc.on('update', (update, origin) => {
    if (origin === 'server') return
    autosave()
  })

  return {
    doc,
    cleanup: () => {
      provider.destroy()
      indexeddb.destroy()
    },
    save,
    provider,
    permanentUserData,
  }
}
