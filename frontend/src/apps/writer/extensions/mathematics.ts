import { createApp, h } from 'vue'
import { Mathematics } from '@tiptap/extension-mathematics'
import { computePosition, flip, shift, offset, autoUpdate } from '@floating-ui/dom'
import { Editor } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import MathPopup from './components/MathPopup.vue'

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    mathematics: {
      /**
       * Opens the math editor popup.
       */
      openMathEditor: (type?: 'inline' | 'block') => ReturnType
    }
  }
}

export const MathematicsExtension = Mathematics.extend({
  addOptions() {
    return {
      ...this.parent?.(),
      katexOptions: {
        throwOnError: false,
      },
      inlineOptions: {
        onClick: (node: any, pos: number) => {
          this.editor.commands.openMathEditor('inline')
        },
      },
      blockOptions: {
        onClick: (node: any, pos: number) => {
          this.editor.commands.openMathEditor('block')
        },
      },
    }
  },

  addCommands() {
    return {
      ...this.parent?.(),
      openMathEditor:
        (type?: 'inline' | 'block') =>
        ({ editor }: { editor: Editor }): boolean => {
          const { state } = editor
          const { from, to, $from } = state.selection

          let existingLatex = ''
          let nodePos: number | undefined = undefined
          let mathType: 'inline' | 'block' = type || 'inline'

          // Check if we're inside a math node
          const inlineMathNode = state.doc.nodeAt(from)
          const blockMathNode = $from.node(-1)

          if (inlineMathNode?.type.name === 'inlineMath') {
            existingLatex = inlineMathNode.attrs.latex || ''
            mathType = 'inline'
            nodePos = from
          } else if (blockMathNode?.type.name === 'blockMath') {
            existingLatex = blockMathNode.attrs.latex || ''
            mathType = 'block'
            nodePos = $from.before(-1)
          } else if (from !== to) {
            // There's a selection, use it as initial content
            existingLatex = state.doc.textBetween(from, to, ' ')
            mathType = type || 'inline'
          }

          openMathEditor(existingLatex, mathType, nodePos, editor)
            .catch(() => {})

          return true
        },
    }
  },

  addKeyboardShortcuts() {
    return {
      'Mod-Shift-e': () => this.editor.commands.openMathEditor('inline'),
      'Mod-Shift-m': () => this.editor.commands.openMathEditor('block'),
    }
  },

  addProseMirrorPlugins() {
    const plugins = this.parent?.() || []

    plugins.push(
      new Plugin({
        key: new PluginKey('mathClickHandler'),
        props: {
          handleDoubleClick: (view, pos, event) => {
            const node = view.state.doc.nodeAt(pos)
            if (node && (node.type.name === 'inlineMath' || node.type.name === 'blockMath')) {
              event.preventDefault()
              this.editor.commands.openMathEditor(
                node.type.name === 'inlineMath' ? 'inline' : 'block'
              )
              return true
            }
            return false
          },
        },
      })
    )

    return plugins
  },
})

interface MathEditorResult {
  latex: string
  type: 'inline' | 'block'
}

function openMathEditor(
  latex: string,
  type: 'inline' | 'block',
  pos: number | undefined,
  editor: Editor
): Promise<void> {
  return new Promise((resolve, reject) => {
    const container = document.createElement('div')
    container.style.position = 'absolute'
    container.style.top = '0'
    container.style.left = '0'
    container.style.zIndex = '9999'
    document.body.appendChild(container)

    let virtualReference: HTMLElement | { getBoundingClientRect: () => DOMRect }

    const selection = window.getSelection()
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0)
      const rect = range.getBoundingClientRect()

      virtualReference = {
        getBoundingClientRect: () =>
          ({
            width: Math.max(rect.width, 200),
            height: rect.height,
            top: rect.top,
            right: rect.right,
            bottom: rect.bottom,
            left: rect.left,
            x: rect.left,
            y: rect.top,
          }) as DOMRect,
      }
    } else {
      virtualReference = editor.view.dom
    }

    let app: ReturnType<typeof createApp> | null = null
    let cleanupAutoUpdate: (() => void) | null = null
    let isDestroyed = false

    const destroy = () => {
      if (isDestroyed) return
      isDestroyed = true

      requestAnimationFrame(() => {
        cleanupAutoUpdate?.()
        app?.unmount()
        container?.remove()
        document.removeEventListener('mousedown', handleClickOutside)
        app = null
        cleanupAutoUpdate = null
      })
    }

    const updatePosition = () => {
      computePosition(virtualReference, container, {
        placement: 'bottom-start',
        middleware: [offset(8), flip(), shift({ padding: 8 })],
      }).then(({ x, y }) => {
        Object.assign(container.style, {
          left: `${x}px`,
          top: `${y}px`,
        })
      })
    }

    const handleUpdate = (newLatex: string, newType: 'inline' | 'block') => {
      if (newLatex === '') {
        // Delete the math node
        if (pos !== undefined) {
          if (type === 'inline') {
            editor.commands.deleteInlineMath({ pos })
          } else {
            editor.commands.deleteBlockMath({ pos })
          }
        }
      } else if (pos !== undefined) {
        // Update existing math node
        if (type === 'inline') {
          editor.commands.updateInlineMath({ latex: newLatex, pos })
        } else {
          editor.commands.updateBlockMath({ latex: newLatex, pos })
        }
      } else {
        // Insert new math node
        if (newType === 'inline') {
          editor.commands.insertInlineMath({ latex: newLatex })
        } else {
          editor.commands.insertBlockMath({ latex: newLatex })
        }
      }
      
      editor.commands.focus()
      destroy()
      resolve()
    }

    app = createApp({
      render() {
        return h(MathPopup, {
          latex,
          type,
          onClose: () => {
            destroy()
            reject('Math editing cancelled')
          },
          onUpdate: handleUpdate,
        })
      },
    })

    app.mount(container)

    cleanupAutoUpdate = autoUpdate(virtualReference, container, updatePosition, {
      animationFrame: true,
    })

    updatePosition()

    const handleClickOutside = (event: MouseEvent) => {
      if (!container.contains(event.target as Node)) {
        destroy()
        reject('Math editing cancelled')
      }
    }

    setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside)
    }, 0)
  })
}

export default MathematicsExtension