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
const syncOfflineChangesStatus = ref(null)

const syncPresentationToServer = async (hadDroppedConnection) => {
	isSaving.value = true

	try {
		const snapshot = await getPresentationFromLocalDB(presentationId.value)

		if (!snapshot || !snapshot.dirty) return

		if (hadDroppedConnection) {
			syncOfflineChangesStatus.value = 'Syncing local changes...'
		}

		await savePresentationDoc(snapshot.content)

		if (hadDroppedConnection) {
			syncOfflineChangesStatus.value = 'All changes synced'
			setTimeout(() => {
				syncOfflineChangesStatus.value = null
			}, 2000)
		}

		await savePresentationToLocalDB({
			...snapshot,
			dirty: false,
			updatedAt: Date.now(),
		})
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

const saveChanges = async () => {
	if (isSaving.value) return

	if (!isDirty.value && syncThumbnail === 0) return

	if (isDirty.value) syncThumbnail = 1
	else syncThumbnail = 0

	const content = getLatestSlideContent()

	await savePresentationToLocalDB({
		id: presentationId.value,
		content: content,
		updatedAt: Date.now(),
		dirty: true,
	})

	if (!navigator.onLine) return

	await syncPresentationToServer()
}

export { syncPresentationToServer, saveChanges, dirtySince, isDirty, syncOfflineChangesStatus }
