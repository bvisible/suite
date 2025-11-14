import * as Y from 'yjs'
import { IndexeddbPersistence } from 'y-indexeddb'
import {
  absolutePositionToRelativePosition,
  ySyncPluginKey,
} from 'y-prosemirror'
import { WebrtcProvider } from 'y-webrtc'


export function useComments(yDoc, editor, id) {
  const commentsDoc = new Y.Doc()
  const indexeddb = new IndexeddbPersistence('wdoc-comments-' + id, commentsDoc)

  const provider = new WebrtcProvider('wdoc-comments-' + id, commentsDoc, {
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
  const yComments = commentsDoc.getMap('comments')
  const newComment = (id, absoluteIndex) => {
    const ystate = ySyncPluginKey.getState(editor.value.view.state)
    const relativePos = absolutePositionToRelativePosition(
      absoluteIndex,
      ystate.type,
      ystate.binding.mapping,
    )
    yComments.set(id, {
      id,
      text: 'Great point!',
      anchor: Y.encodeRelativePosition(relativePos),
      timestamp: Date.now(),
    })
  }
  return { newComment, yComments }
}
