import { io } from 'socket.io-client'

export function initSocket() {
  let siteName = window.site_name || 'drive.localhost'

  let default_port = __SOCKETIO_PORT__
  let port = window.location.port ? `:${default_port}` : ''
  let protocol = port ? 'http' : 'https'
  let host = window.location.hostname

  let url = `${protocol}://${host}${port}/${siteName}`
  let socket = io(url, {
    withCredentials: true,
    reconnectionAttempts: 5,
  })
  socket.on('connect_error', (data) => {
    console.log(data)
  })
  return socket
}
