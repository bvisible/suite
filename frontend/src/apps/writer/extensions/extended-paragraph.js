import { Paragraph } from '@tiptap/extension-paragraph'

const ExtendedParagraph = Paragraph.extend({
  addAttributes() {
    return {
      lineHeight: {
        default: null,
        parseHTML: (el) => el.style.lineHeight || null,
        renderHTML: (attrs) =>
          attrs.lineHeight ? { style: `line-height: ${attrs.lineHeight}` } : {},
      },
      spacingBefore: {
        default: null,
        parseHTML: (el) => el.style.marginTop || null,
        renderHTML: (attrs) =>
          attrs.spacingBefore
            ? { style: `margin-top: ${attrs.spacingBefore}` }
            : {},
      },
      spacingAfter: {
        default: null,
        parseHTML: (el) => el.style.marginBottom || null,
        renderHTML: (attrs) =>
          attrs.spacingAfter
            ? { style: `margin-bottom: ${attrs.spacingAfter}` }
            : {},
      },
    }
  },
})

export default ExtendedParagraph
