import { io, type Socket } from "socket.io-client";

declare global {
	interface Window {
		site_name?: string;
		socketio_port?: number | string;
	}
}

let socket: Socket | null = null;

export function initSocket(): Socket {
	const host = window.location.hostname;
	const siteName = window.site_name || "sae.local";
	// `socketio_port` was imported from sites/common_site_config.json in the
	// standalone app (a path outside the suite frontend root that Vite's
	// fs.allow rejects). Read it from window boot data instead, with a dev
	// fallback. Only used in dev (when window.location.port is set).
	const socketio_port = window.socketio_port ?? 9000;
	const port = window.location.port ? `:${socketio_port}` : "";
	const protocol = port ? "http" : "https";
	const url = `${protocol}://${host}${port}/${siteName}`;

	socket = io(url, {
		withCredentials: true,
		transports: ["websocket", "polling"],
		reconnectionAttempts: 5,
	});

	return socket;
}

export function useSocket(): Socket | null {
	return socket;
}
