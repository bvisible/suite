import { BubbleMenu, BubbleMenuView } from '@tiptap/extension-bubble-menu'
import { Plugin } from '@tiptap/pm/state'

export const ExtendedBubbleMenu = BubbleMenu.extend({
  addProseMirrorPlugins() {
    if (!this.options.element) {
      return []
    }

    return [
      new Plugin({
        key: this.options.pluginKey,
        view: (view) => {
          console.log('heyy')
          const original = new BubbleMenuView({
            view,
            ...this.options,
            editor: this.editor,
          })

          // inject your middleware
          const orig = original.middlewares.bind(original)
          original.middlewares = () => {
            const arr = orig()
            arr.push(myMiddleware())
            return arr
          }

          return original
        },
      }),
    ]
  },
})
