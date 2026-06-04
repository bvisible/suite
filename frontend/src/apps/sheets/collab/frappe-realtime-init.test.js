// @vitest-environment node

import { describe, it, expect, vi } from 'vitest'
import { ensureFrappeRealtime } from './frappe-realtime-init.js'

function _stubWindow({ origin = 'https://acme.frappe.cloud', dev_server = false, boot = {} } = {}) {
	return {
		location: { origin },
		dev_server,
		frappe: { boot },
	}
}

function _stubIoFactory() {
	const calls = []
	const handlers = new Map()
	const socket = {
		connected: false,
		id: '',
		on:   vi.fn((e, cb) => {
			if (!handlers.has(e)) handlers.set(e, new Set())
			handlers.get(e).add(cb)
		}),
		off:  vi.fn(),
		emit: vi.fn(),
		_fire: (e, ...args) => handlers.get(e)?.forEach(cb => cb(...args)),
	}
	const factory = (url, opts) => { calls.push({ url, opts }); return socket }
	return { factory, socket, calls }
}

describe('ensureFrappeRealtime', () => {
	it('connects to the site namespace on production (no port splice)', () => {
		const w = _stubWindow({ origin: 'https://acme.frappe.cloud', boot: { sitename: 'acme.frappe.cloud' } })
		const { factory, calls } = _stubIoFactory()
		const shim = ensureFrappeRealtime(undefined, { window: w, ioFactory: factory })
		expect(shim).toBeTruthy()
		expect(calls[0].url).toBe('https://acme.frappe.cloud/acme.frappe.cloud')
		expect(calls[0].opts.withCredentials).toBe(true)
	})

	it('splices the socketio_port on dev_server', () => {
		const w = _stubWindow({
			origin: 'http://localhost:8001',
			dev_server: true,
			boot: { sitename: 'erpnext.localhost', socketio_port: 9001 },
		})
		const { factory, calls } = _stubIoFactory()
		ensureFrappeRealtime(undefined, { window: w, ioFactory: factory })
		expect(calls[0].url).toBe('http://localhost:9001/erpnext.localhost')
	})

	it('returns null and logs when sitename is missing', () => {
		const w = _stubWindow({ boot: {} })
		const { factory } = _stubIoFactory()
		const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
		const shim = ensureFrappeRealtime(undefined, { window: w, ioFactory: factory })
		expect(shim).toBeNull()
		expect(warn).toHaveBeenCalled()
		warn.mockRestore()
	})

	it('is idempotent — second call returns the existing shim, no reconnect', () => {
		const w = _stubWindow({ boot: { sitename: 's1' } })
		const { factory, calls } = _stubIoFactory()
		const a = ensureFrappeRealtime(undefined, { window: w, ioFactory: factory })
		const b = ensureFrappeRealtime(undefined, { window: w, ioFactory: factory })
		expect(b).toBe(a)
		expect(calls.length).toBe(1)
	})

	it('exposes on/off/emit pass-throughs and live connected/id getters', () => {
		const w = _stubWindow({ boot: { sitename: 's1' } })
		const { factory, socket } = _stubIoFactory()
		const shim = ensureFrappeRealtime(undefined, { window: w, ioFactory: factory })
		// pass-through
		const cb = () => {}
		shim.on('evt', cb); expect(socket.on).toHaveBeenCalledWith('evt', cb)
		shim.off('evt', cb); expect(socket.off).toHaveBeenCalledWith('evt', cb)
		shim.emit('evt', 1, 2); expect(socket.emit).toHaveBeenCalledWith('evt', 1, 2)
		// live state
		expect(shim.connected).toBe(false)
		expect(shim.id).toBe('')
		socket.connected = true; socket.id = 'sock-123'
		expect(shim.connected).toBe(true)
		expect(shim.id).toBe('sock-123')
	})
})
