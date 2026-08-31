import type { Component, VNodeChild } from 'vue'

export type ComboboxVariant = 'subtle' | 'outline' | 'ghost'

export type SelectableOption = {
  type?: 'option'
  label: string
  value: string
  icon?: string | Component
  disabled?: boolean
}

export type CustomOption = {
  type: 'custom'
  label: string
  key: string
  icon?: string | Component
  disabled?: boolean
  onClick: (context: { query: string }) => void
  keepOpen?: boolean
  slot?: string
  slots?: { label?: (context: { query: string }) => VNodeChild }
  condition?: (context: { query: string }) => boolean
}

export type SimpleOption = string | SelectableOption | CustomOption
export type GroupedOption = { group: string; options: SimpleOption[] }
export type ComboboxOption = SimpleOption | GroupedOption

export interface ComboboxProps {
  variant?: ComboboxVariant
  options: Array<ComboboxOption>
  modelValue?: string | null
  placeholder?: string
  disabled?: boolean
  openOnFocus?: boolean
  openOnClick?: boolean
  placement?: 'start' | 'center' | 'end'
}
export interface TagInputProps {
  modelValue?: string | null
  placeholder?: string
  disabled?: boolean
  renderIcon?: Function
}
