import { ref } from 'vue'
import { presentationId, savePresentationDoc } from '@/apps/slides/stores/presentation'
import { slides } from '@/apps/slides/stores/slide'
import { cloneObj } from '@/apps/slides/utils/helpers'

const DB_NAME = 'slides-db'
const DB_VERSION = 1
const STORE = 'presentations'

let db = null

const openDB = () => {
  if (db) {
    return Promise.resolve(db)
  }

  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)

    req.onupgradeneeded = () => {
      const db = req.result

      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'id' })
      }
    }

    req.onsuccess = () => {
      db = req.result
      resolve(db)
    }

    req.onerror = () => {
      reject(req.error)
    }
  })
}

const savePresentationToLocalDB = async data => {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    const store = tx.objectStore(STORE)

    const req = store.put(data)
    req.onerror = () => {
      reject(req.error)
    }

    tx.oncomplete = () => {
      resolve()
    }

    tx.onerror = () => {
      reject(tx.error)
    }
  })
}

const getPresentationFromLocalDB = async id => {
  if (id === undefined || id === null || id === '') {
    return null
  }

  const db = await openDB()

  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly')
    const store = tx.objectStore(STORE)

    const req = store.get(id)

    req.onsuccess = () => {
      resolve(req.result)
    }

    req.onerror = () => {
      reject(req.error)
    }
  })
}

// explicit dirty flag set by every mutation path
const dirty = ref(false)

const markDirty = () => {
  dirty.value = true
}

const markClean = () => {
  dirty.value = false
}

const isSaving = ref(false)

const syncSnapshotToServer = async snapshot => {
  await savePresentationDoc(snapshot.content)

  // after successful sync, make sure local copy is marked as clean so it's not synced again
  await savePresentationToLocalDB({
    ...snapshot,
    dirty: false,
    updatedAt: Date.now(),
  })
}

const syncPresentationToServer = async () => {
  try {
    const snapshot = await getPresentationFromLocalDB(presentationId.value)
    if (!snapshot || !snapshot.dirty) return

    // if there's an unsynced snapshot locally, sync it to server
    await syncSnapshotToServer(snapshot)
  } catch (err) {
    console.error('Sync to server failed: ', err)
  }
}

const getLatestSlideContent = () => {
  const latestContent = slides.value
  return cloneObj(latestContent)
}

const saveCurrentState = async () => {
  if (isSaving.value) return
  if (!slides.value?.length || !presentationId.value) return

  isSaving.value = true

  try {
    const content = getLatestSlideContent()

    // save latest content to indexedDB with dirty flag since it's not yet synced to server
    await savePresentationToLocalDB({
      id: presentationId.value,
      content: content,
      updatedAt: Date.now(),
      dirty: true,
    })

    // changes are persisted locally (and queued for sync), so the editor
    // state is no longer ahead of storage
    markClean()

    // if offline, do not attempt to sync to server
    if (!navigator.onLine) return

    // if online, sync to server
    await syncPresentationToServer()
  } finally {
    isSaving.value = false
  }
}

const saveChanges = async () => {
  if (!dirty.value) return
  await saveCurrentState()
}

export { saveCurrentState, saveChanges, isSaving, dirty, markDirty, markClean }
