import { Extension } from '@tiptap/core'
import { Decoration, DecorationSet } from '@tiptap/pm/view'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import {
  relativePositionToAbsolutePosition,
  ySyncPluginKey,
} from '@tiptap/y-tiptap'

import * as Y from 'yjs'
export const commentPluginKey = new PluginKey('comment-anchors')

export const rebuild = (editor) => {
  editor
    .chain()
    .command(({ tr }) => {
      tr.setMeta(commentPluginKey, { rebuild: true })
      return true
    })
    .run()
}

export const getEditorPos = (relativePos, editor) => {
  const ystate = ySyncPluginKey.getState(editor.state)
  const collab = editor.extensionManager.extensions.find(
    (ext) => ext.name === 'collaboration',
  )

  return relativePositionToAbsolutePosition(
    collab?.options.document,
    ystate.type,
    Y.decodeRelativePosition(relativePos),
    ystate.binding.mapping,
  )
}

const createDecorations = (editor, yDoc, comments, active, showResolved) => {
  try {
    if (!comments._map.size) return DecorationSet.empty
    const ystate = ySyncPluginKey.getState(editor.state)
    const decos = []
    comments.forEach((comment) => {
      if (
        !comment.anchor.from ||
        (!showResolved && comment.resolved) ||
        !ystate
      )
        return
      const from = relativePositionToAbsolutePosition(
        yDoc,
        ystate.type,
        Y.decodeRelativePosition(comment.anchor.from),
        ystate.binding.mapping,
      )
      const to = relativePositionToAbsolutePosition(
        yDoc,
        ystate.type,
        Y.decodeRelativePosition(comment.anchor.to),
        ystate.binding.mapping,
      )
      console.log('HOHOHO', from, to)

      decos.push(
        Decoration.inline(from, to, {
          nodeName: 'span',
          class: comment.id === active ? 'active' : '',
          'data-comment-name': comment.id,
          'data-resolved': comment.resolved,
        }),
      )
    })
    return DecorationSet.create(editor.state.doc, decos)
  } catch (e) {
    return DecorationSet.empty
  }
}
export const CommentExtension = Extension.create({
  name: 'commentExtension',

  addOptions() {
    return {
      comments: [],
      doc: null,
      activeComment: null,
      onActivated: null,
      onDecorationsPainted: null,
    }
  },

  addProseMirrorPlugins() {
    const ext = this

    return [
      new Plugin({
        key: commentPluginKey,
        state: {
          init(_, state) {
            const {
              doc,
              comments,
              activeComment,
              showResolved,
              onDecorationsPainted,
            } = ext.options
            const decos = createDecorations(
              ext.editor,
              doc,
              comments,
              activeComment.value,
              showResolved.value,
            )
            if (onDecorationsPainted) setTimeout(onDecorationsPainted, 100)
            return decos
          },

          apply(tr, oldSet) {
            const { doc, comments, activeComment, showResolved } = ext.options
            const rebuild = tr.getMeta(commentPluginKey)?.rebuild
            if ((!tr.docChanged && !rebuild) || !comments._map.size)
              return oldSet

            const isRemote = tr.getMeta('y-sync$')?.isChangeOrigin
            if (isRemote || rebuild) {
              const ySyncMeta = tr.getMeta('y-sync$')
              return createDecorations(
                ext.editor,
                doc,
                comments,
                activeComment.value,
                showResolved.value,
              )
            }
            return oldSet.map(tr.mapping, tr.doc)
          },
        },
        props: {
          decorations(state) {
            return commentPluginKey.getState(state)
          },

          handleClick(view, pos, event) {
            const el = event.target.closest('[data-comment-name]')
            if (el) {
              const id = el.getAttribute('data-comment-name')
              ext.options.onActivated?.(id)
              return true
            }
            return false
          },
        },
      }),
    ]
  },
})
