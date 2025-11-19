import * as Y from 'yjs'
import { IndexeddbPersistence } from 'y-indexeddb'
import { WebrtcProvider } from 'y-webrtc'
import { toUint8Array, fromUint8Array } from 'js-base64'
import { debounce, toast } from 'frappe-ui'
import {
  absolutePositionToRelativePosition,
  ySyncPluginKey,
} from 'y-prosemirror'
import { rebuild } from '@/extensions/comments'

import store from '@/store'

const REALTIME_CONFIG = {
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
}

export const useComments = (document, editor) => {
  const commentsDoc = new Y.Doc()
  if (document.doc.ycomments) {
    Y.applyUpdate(commentsDoc, toUint8Array(document.doc.ycomments))
  }

  const dbComments = new IndexeddbPersistence(
    'wdoc-comments-' + document.doc.name,
    commentsDoc,
  )
  const providerComments = new WebrtcProvider(
    'wdoc-comments-' + document.doc.name,
    commentsDoc,
    REALTIME_CONFIG,
  )

  const comments = commentsDoc.getMap('comments')
  const newComment = (id, from, to, owner, anchorText) => {
    const ystate = ySyncPluginKey.getState(editor.value.view.state)

    comments.set(id, {
      id,
      new: true,
      creation: Date.now(),
      owner,
      replies: [],
      anchorText,
      anchor: {
        from: Y.encodeRelativePosition(
          absolutePositionToRelativePosition(
            from,
            ystate.type,
            ystate.binding.mapping,
          ),
        ),
        to: Y.encodeRelativePosition(
          absolutePositionToRelativePosition(
            to,
            ystate.type,
            ystate.binding.mapping,
          ),
        ),
      },
    })
    rebuild(editor.value)
  }
  const saveComments = async () => {
    const data = fromUint8Array(Y.encodeStateAsUpdate(commentsDoc))
    document.saveComments.submit({ data })
  }
  const cleanup = () => {
    providerComments.destroy()
    dbComments.destroy()
  }
  return { saveComments, newComment, comments, cleanup }
}


export function useYjs(document, editor, edited) {
  const doc = new Y.Doc()
  if (document.doc.content || document.doc.updates.length)
    Y.applyUpdate(
      doc,
      Y.mergeUpdates([
        toUint8Array(document.doc.content),
        ...document.doc.updates.map(({ data }) => toUint8Array(data)),
      ]),
    )

  let serverStateVector = Y.encodeStateVector(doc)

  const db = new IndexeddbPersistence('wdoc-' + document.doc.name, doc)

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
  const provider = new WebrtcProvider(
    'wdoc-' + document.doc.name,
    doc,
    REALTIME_CONFIG,
  )
  const permanentUserData = new Y.PermanentUserData(doc)
  permanentUserData.setUserMapping(doc, doc.clientID, store.state.user.id)

  doc.on('update', (_, origin) => {
    if (origin !== 'server') autosave()
  })

  // Comments
  const { cleanup: cleanupComments, ...commentsData } = useComments(document, editor)

  return {
    doc,
    cleanup: () => {
      provider.destroy()
      db.destroy()
      cleanupComments()
    },
    save,
    provider,
    permanentUserData,
    ...commentsData 
  }
}
