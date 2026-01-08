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

export { savePresentationToLocalDB }
