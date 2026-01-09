import { ref, computed } from 'vue'
import {
	presentationDoc,
	presentationId,
	hasStateChanged,
	savePresentationDoc,
} from '@/stores/presentation'
import { slides } from '@/stores/slide'
import { cloneObj } from '@/utils/helpers'

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

const savePresentationToLocalDB = async (data) => {
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

const getPresentationFromLocalDB = async (id) => {
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

const dirtySince = ref(null)

const isDirty = computed(() => {
	if (!presentationDoc.value || !slides.value) return false

	const original = JSON.parse(JSON.stringify(presentationDoc.value.slides || []))
	const current = JSON.parse(JSON.stringify(slides.value || []))

	return hasStateChanged(original, current)
})

const isSaving = ref(false)

let syncThumbnail = 0

const syncOfflineStatus = ref(null)

const syncSnapshotToServer = async (wasConnectionRestored, snapshot) => {
	// if connection was restored, syncing was not triggered by auto-save
	// so add badge after coming back online
	if (wasConnectionRestored) {
		syncOfflineStatus.value = 'Syncing'
	}

	await savePresentationDoc(snapshot.content)

	if (wasConnectionRestored) {
		syncOfflineStatus.value = 'Synced'
		setTimeout(() => {
			syncOfflineStatus.value = null
		}, 2000)
	}

	// after successful sync, make sure local copy is marked as clean so it's not synced again
	await savePresentationToLocalDB({
		...snapshot,
		dirty: false,
		updatedAt: Date.now(),
	})
}

const syncPresentationToServer = async (wasConnectionRestored) => {
	isSaving.value = true

	try {
		const snapshot = await getPresentationFromLocalDB(presentationId.value)
		if (!snapshot || !snapshot.dirty) return

		// if there's an unsynced snapshot locally, sync it to server
		syncSnapshotToServer(wasConnectionRestored, snapshot)
	} catch (err) {
		console.error('Sync to server failed: ', err)
	} finally {
		isSaving.value = false
	}
}

const getLatestSlideContent = () => {
	const latestContent = slides.value
	return cloneObj(latestContent)
}

const saveCurrentState = async () => {
	const content = getLatestSlideContent()

	// save latest content to indexedDB with dirty flag since it's not yet synced to server
	await savePresentationToLocalDB({
		id: presentationId.value,
		content: content,
		updatedAt: Date.now(),
		dirty: true,
	})

	// if offline, do not attempt to sync to server
	if (!navigator.onLine) return

	// if online, sync to server
	await syncPresentationToServer()
}

const saveChanges = () => {
	if (isSaving.value) return

	if (!isDirty.value && syncThumbnail === 0) return

	if (isDirty.value) syncThumbnail = 1
	else syncThumbnail = 0

	saveCurrentState()
}

export { syncPresentationToServer, saveChanges, dirtySince, isDirty, syncOfflineStatus }
