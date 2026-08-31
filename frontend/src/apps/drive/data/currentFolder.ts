import { ref } from 'vue'

export type CurrentFolder = {
  name: string
  entities: Record<string, unknown>[]
}

export const currentFolder = ref<CurrentFolder>({
  name: '',
  entities: [],
})

export function setCurrentFolder(
  payload: Partial<CurrentFolder> | null,
) {
  if (payload === null) {
    currentFolder.value = { name: '', entities: [] }
    return
  }
  currentFolder.value = { ...currentFolder.value, ...payload }
}
