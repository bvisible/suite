//// Neoffice — added file (no upstream equivalent): the tests of blurField.ts (maintenance#1623).
import { describe, expect, it, vi } from 'vitest'

import { blurInput, inputOf } from './blurField'

const input = () => ({ tagName: 'INPUT', blur: vi.fn() }) as unknown as HTMLInputElement

describe('blurInput', () => {
	it('blurs the element the ref still exposes as `el`', () => {
		const field = input()
		blurInput({ el: field })
		expect(field.blur).toHaveBeenCalledOnce()
	})

	it('finds the root when `el` is gone, which is the case that threw on every Escape', () => {
		const field = input()
		expect(() => blurInput({ $el: field })).not.toThrow()
		expect(field.blur).toHaveBeenCalledOnce()
	})

	it('finds the input inside a wrapper root', () => {
		const field = input()
		const wrapper = { tagName: 'DIV', querySelector: vi.fn(() => field) } as unknown as HTMLElement
		blurInput({ $el: wrapper })
		expect(wrapper.querySelector).toHaveBeenCalledWith('input')
		expect(field.blur).toHaveBeenCalledOnce()
	})

	it('does nothing, and does not throw, with no ref, an empty ref or a root without an input', () => {
		expect(() => blurInput(undefined)).not.toThrow()
		expect(() => blurInput(null)).not.toThrow()
		expect(() => blurInput({})).not.toThrow()
		expect(inputOf({ $el: { tagName: 'DIV', querySelector: () => null } as unknown as HTMLElement })).toBeNull()
	})
})
