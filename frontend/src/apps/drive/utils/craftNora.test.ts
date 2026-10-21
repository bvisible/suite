//// Neoffice — added file (no upstream equivalent): the way to Nora the Drive page offers a Craft editor (craftNora.js).
import { describe, expect, it, vi } from 'vitest'

import { MAX_BODY, NORA_PATHS, noraCall, offerNora, plainArguments } from './craftNora'

const SEND = '/api/method/nora.api.chat.start_or_resume_thread'
const ARGS = JSON.stringify({ message: 'Bonjour', context: '{"surface":"editor","app":"word"}', block: 0 })

function server(status = 200, text = '{"message":{"thread_id":"nora-1"}}') {
  return vi.fn(async (_url: string, _init: RequestInit) => ({ status, text: async () => text }) as unknown as Response)
}

describe('noraCall', () => {
  it('makes a call of the protocol at the page’s own origin, with its session and its CSRF token', async () => {
    const fetch = server()
    const call = noraCall({ fetch, csrfToken: () => 'the-token' })
    expect(await call(SEND, ARGS)).toEqual({ status: 200, body: '{"message":{"thread_id":"nora-1"}}' })
    expect(fetch).toHaveBeenCalledOnce()
    const [url, init] = fetch.mock.calls[0]
    // A path, never an origin: the call stays on the page's own.
    expect(url).toBe(SEND)
    expect(init).toMatchObject({ method: 'POST', credentials: 'same-origin', redirect: 'error', body: ARGS })
    expect(init.headers).toEqual({
      Accept: 'application/json',
      'Content-Type': 'application/json',
      'X-Frappe-CSRF-Token': 'the-token',
    })
  })

  it('takes the five calls of the protocol, each one', async () => {
    expect(NORA_PATHS.size).toBe(5)
    for (const path of NORA_PATHS) {
      const fetch = server()
      expect((await noraCall({ fetch })(path, '{}')).status, path).toBe(200)
      expect(fetch.mock.calls[0][0]).toBe(path)
    }
  })

  it('refuses any other path before it leaves the page, an address of another origin among them', async () => {
    const fetch = server()
    const call = noraCall({ fetch, csrfToken: () => 'the-token' })
    for (const path of [
      '/api/method/frappe.client.get_list',
      '/api/method/nora.api.chat.start_or_resume_thread/x',
      '/api/method/nora.api.v2.memory.read_memory',
      '/api/v2/method/nora.api.chat.post_message',
      'https://elsewhere.example/api/method/nora.api.chat.post_message',
      '//elsewhere.example/api/method/nora.api.chat.post_message',
      '',
    ]) {
      expect(await call(path, ARGS), path).toEqual({ status: 403, body: '' })
    }
    expect(fetch).not.toHaveBeenCalled()
  })

  it('refuses a body that names `cmd`, or that is not a plain JSON object', async () => {
    const fetch = server()
    const call = noraCall({ fetch })
    for (const body of ['{"cmd":"frappe.client.delete"}', '[1]', '"text"', 'null', '42', 'not json']) {
      expect(await call(SEND, body), body).toEqual({ status: 400, body: '' })
    }
    expect(fetch).not.toHaveBeenCalled()
  })

  it('refuses a body that is too large', async () => {
    const fetch = server()
    expect(await noraCall({ fetch })(SEND, `{"message":"${'a'.repeat(MAX_BODY)}"}`)).toEqual({ status: 413, body: '' })
    expect(fetch).not.toHaveBeenCalled()
  })

  it('sends no CSRF header when the page has no token, or only its unrendered template', async () => {
    for (const token of [undefined, '', '{{ csrf_token }}']) {
      const fetch = server()
      await noraCall({ fetch, csrfToken: () => token })(SEND, ARGS)
      expect(fetch.mock.calls[0][1].headers, String(token)).not.toHaveProperty('X-Frappe-CSRF-Token')
    }
  })

  it('hands back a refusal as the server said it, for the pane to show', async () => {
    const refusal = '{"exc_type":"PermissionError","_server_messages":"[]"}'
    expect(await noraCall({ fetch: server(403, refusal) })(SEND, ARGS)).toEqual({ status: 403, body: refusal })
  })

  it('answers status 0 with the reason when nothing came back', async () => {
    const fetch = vi.fn(async () => {
      throw new TypeError('Failed to fetch')
    })
    const answer = await noraCall({ fetch })(SEND, ARGS)
    expect(answer.status).toBe(0)
    expect(JSON.parse(answer.body).exception).toContain('Failed to fetch')
  })

  it('gives up on a call that never answers', async () => {
    const fetch = vi.fn(
      (_url: string, init: RequestInit) =>
        new Promise<Response>((_resolve, reject) => init.signal?.addEventListener('abort', () => reject(new Error('aborted')))),
    )
    const answer = await noraCall({ fetch, timeoutMs: 5 })(SEND, ARGS)
    expect(answer.status).toBe(0)
  })
})

describe('plainArguments', () => {
  it('writes a plain object again, and an empty body as an empty one', () => {
    expect(plainArguments('{"thread_id":"t"}')).toBe('{"thread_id":"t"}')
    expect(plainArguments('')).toBe('{}')
  })
})

describe('offerNora', () => {
  it('puts the editor’s function on the page, and takes it back', async () => {
    const page: Record<string, unknown> = {}
    const withdraw = offerNora(page, 'wordcraft', { fetch: server() })
    expect(typeof page.wordcraftNoraCall).toBe('function')
    withdraw()
    expect(page).not.toHaveProperty('wordcraftNoraCall')
  })

  it('names each editor’s function after its prefix', () => {
    for (const prefix of ['wordcraft', 'gridcraft', 'deckcraft', 'pdfcraft']) {
      const page: Record<string, unknown> = {}
      offerNora(page, prefix, {})
      expect(Object.keys(page), prefix).toEqual([`${prefix}NoraCall`])
    }
  })

  it('offers nothing to an editor it does not know', () => {
    const page: Record<string, unknown> = {}
    const withdraw = offerNora(page, 'mailcraft', {})
    offerNora(page, undefined as unknown as string, {})
    expect(page).toEqual({})
    withdraw()
    expect(page).toEqual({})
  })

  it('leaves alone a function put there by someone else since', () => {
    const page: Record<string, unknown> = {}
    const withdraw = offerNora(page, 'gridcraft', {})
    const theirs = () => undefined
    page.gridcraftNoraCall = theirs
    withdraw()
    expect(page.gridcraftNoraCall).toBe(theirs)
  })
})
