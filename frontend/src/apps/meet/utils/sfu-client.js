// Direct SFU Client Manager - Connects directly to SFU without relay
// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

import { frappeRequest } from "frappe-ui";
import { io } from "socket.io-client";

class SFUClient {
	constructor() {
		this.socket = null;
		this.connected = false;
		this.authToken = null;
		this.meetingId = null;
		this.userId = null;
		this.sfuUrl = null;
		this.sfuPort = null;
		this.eventHandlers = {};

		this.setupDefaultHandlers();
	}

	setupDefaultHandlers() {
		this.eventHandlers = {
			connect: () => {
				console.log("✅ Connected to SFU");
				this.connected = true;
			},
			disconnect: () => {
				console.log("🔌 Disconnected from SFU");
				this.connected = false;
			},
			connect_error: (error) => {
				console.error("❌ SFU connection error:", error);
				this.connected = false;
			},
			participant_joined: (data) => {
				console.log("👥 Participant joined:", data);
			},
			participant_left: (data) => {
				console.log("👋 Participant left:", data);
			},
			producer_created: (data) => {
				console.log("🎥 Producer created:", data);
			},
			producer_closed: (data) => {
				console.log("❌ Producer closed:", data);
			},
			consumer_created: (data) => {
				console.log("🎬 Consumer created:", data);
			},
			consumer_closed: (data) => {
				console.log("❌ Consumer closed:", data);
			},
			media_control_update: (data) => {
				console.log("🎛️ Media control update:", data);
			},
			screen_share_started: (data) => {
				console.log("🖥️ Screen share started:", data);
			},
			screen_share_stopped: (data) => {
				console.log("🖥️ Screen share stopped:", data);
			},
			webrtc_offer: (data) => {
				console.log("📡 WebRTC offer received:", data);
			},
			webrtc_answer: (data) => {
				console.log("📡 WebRTC answer received:", data);
			},
			ice_candidate: (data) => {
				console.log("🧊 ICE candidate received:", data);
			},
			"chat:message": (data) => {
				console.log("💬 Chat message:", data);
			},
		};
	}

	async connect(meetingId) {
		try {
			// Get SFU connection details from Frappe server
			const response = await frappeRequest({
				url: "sae.api.meeting.get_sfu_connection_details",
				params: { meeting_id: meetingId },
			});

			if (!response.success) {
				throw new Error(
					response.error || "Failed to get SFU connection details",
				);
			}

			const { sfu_url, sfu_port, auth_token, user_id, meeting_id, user_data } =
				response;

			this.authToken = auth_token;
			this.meetingId = meeting_id;
			this.userId = user_id;
			this.sfuUrl = sfu_url;
			this.sfuPort = sfu_port;

			let sfuEndpoint;
			const urlObj = new URL(sfu_url);
			const isSecured = urlObj.protocol === "https:";
			if (isSecured) {
				sfuEndpoint = urlObj.origin;
			} else {
				sfuEndpoint = `${urlObj.protocol}//${urlObj.hostname}:${sfu_port}`;
			}

			try {
				const healthResponse = await fetch(`${sfuEndpoint}/health`);
				if (!healthResponse.ok) {
					console.warn(
						"⚠️ SFU health check failed, but attempting connection anyway",
					);
				}
			} catch (fetchError) {
				console.warn(
					"⚠️ SFU health check failed:",
					fetchError.message,
					"- attempting socket connection anyway",
				);
			}

			this.socket = io(sfuEndpoint, {
				auth: {
					token: auth_token,
				},
				reconnection: true,
				reconnectionAttempts: 5,
				reconnectionDelay: 1000,
				// Add transport configuration to handle XHR poll errors
				transports: ["websocket", "polling"],
				upgrade: true,
				// Add timeout configurations
				timeout: 20000,
				forceNew: true,
				// Add additional CORS handling
				withCredentials: false,
			});

			// Register event handlers
			for (const [event, handler] of Object.entries(this.eventHandlers)) {
				this.socket.on(event, handler);
			}

			// Wait for connection
			return new Promise((resolve, reject) => {
				// Add more detailed error handling
				this.socket.on("connect", () => {
					this.connected = true;
					resolve();
				});

				this.socket.on("connect_error", (error) => {
					console.error("❌ Failed to connect to SFU:", error);
					console.error("❌ SFU endpoint:", sfuEndpoint);
					console.error("❌ Error details:", {
						message: error.message,
						description: error.description,
						context: error.context,
						type: error.type,
					});
					this.connected = false;
					reject(new Error(`SFU connection failed: ${error.message || error}`));
				});

				this.socket.on("disconnect", (reason) => {
					console.log("🔌 Disconnected from SFU:", reason);
					this.connected = false;
				});

				// Set timeout
				setTimeout(() => {
					if (!this.connected) {
						console.error("❌ SFU connection timeout after 10 seconds");
						reject(new Error("SFU connection timeout"));
					}
				}, 10000);
			});
		} catch (error) {
			console.error("❌ Error connecting to SFU:", error);
			throw error;
		}
	}

	disconnect() {
		if (this.socket) {
			this.socket.disconnect();
			this.socket = null;
		}
		this.connected = false;
		this.authToken = null;
		this.meetingId = null;
		this.userId = null;
	}

	// WebRTC operations - direct to SFU
	async getRouterRtpCapabilities() {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit("get_router_rtp_capabilities", {}, (response) => {
				if (response.success) {
					resolve(response.rtpCapabilities);
				} else {
					reject(new Error(response.error));
				}
			});
		});
	}

	async createWebRtcTransport(direction) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit("create_webrtc_transport", { direction }, (response) => {
				if (response.success) {
					const { id, iceParameters, iceCandidates, dtlsParameters } = response;
					resolve({ id, iceParameters, iceCandidates, dtlsParameters });
				} else {
					console.error(`❌ SFU transport creation failed: ${response.error}`);
					reject(new Error(response.error || "Failed to create transport"));
				}
			});
		});
	}

	async connectWebRtcTransport(transportId, dtlsParameters) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			console.log(`🔗 Connecting transport ${transportId} to SFU...`);
			console.log(`📋 DTLS Parameters: ${JSON.stringify(dtlsParameters)}`);

			this.socket.emit(
				"connect_webrtc_transport",
				{
					transportId,
					dtlsParameters,
				},
				(response) => {
					console.log(
						`📡 SFU transport connection response: ${JSON.stringify(response)}s`,
					);

					if (response.success) {
						console.log(`✅ Transport ${transportId} connected successfully`);
						resolve();
					} else {
						console.error(
							`❌ SFU transport connection failed: ${response.error}`,
						);
						reject(new Error(response.error || "Failed to connect transport"));
					}
				},
			);
		});
	}

	async createProducer(transportId, rtpParameters, kind, appData = {}) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit(
				"create_producer",
				{
					transportId,
					rtpParameters,
					kind,
					appData,
				},
				(response) => {
					if (response.success) {
						resolve(response);
					} else {
						reject(new Error(response.error));
					}
				},
			);
		});
	}

	async createConsumer(transportId, producerId, rtpCapabilities) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit(
				"create_consumer",
				{
					transportId,
					producerId,
					rtpCapabilities,
				},
				(response) => {
					console.log(`📡 SFU create_consumer response: ${response}`);
					if (response.success) {
						resolve(response);
					} else {
						reject(new Error(response.error));
					}
				},
			);
		});
	}

	async getExistingProducers(roomId = null) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			const requestData = roomId ? { roomId } : {};
			this.socket.emit("get_existing_producers", requestData, (response) => {
				if (response.success) {
					resolve(response.producers);
				} else {
					reject(new Error(response.error));
				}
			});
		});
	}

	async getRoomParticipants() {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit("get_room_participants", {}, (response) => {
				if (response.success) {
					resolve(response.participants);
				} else {
					reject(new Error(response.error));
				}
			});
		});
	}

	async closeProducer(producerId) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit("close_producer", { producerId }, (response) => {
				if (response.success) {
					resolve();
				} else {
					reject(new Error(response.error));
				}
			});
		});
	}

	async closeConsumer(consumerId) {
		return new Promise((resolve, reject) => {
			if (!this.connected) {
				reject(new Error("Not connected to SFU"));
				return;
			}

			this.socket.emit("close_consumer", { consumerId }, (response) => {
				if (response.success) {
					resolve();
				} else {
					reject(new Error(response.error));
				}
			});
		});
	}

	// WebRTC signaling
	sendWebRtcOffer(targetUser, signalData) {
		if (!this.connected) {
			throw new Error("Not connected to SFU");
		}
		this.socket.emit("webrtc_offer", { targetUser, signalData });
	}

	sendWebRtcAnswer(targetUser, signalData) {
		if (!this.connected) {
			throw new Error("Not connected to SFU");
		}
		this.socket.emit("webrtc_answer", { targetUser, signalData });
	}

	sendIceCandidate(targetUser, signalData) {
		if (!this.connected) {
			throw new Error("Not connected to SFU");
		}
		this.socket.emit("ice_candidate", { targetUser, signalData });
	}

	// Media control
	sendMediaControl(action) {
		if (!this.connected) {
			throw new Error("Not connected to SFU");
		}
		this.socket.emit("media_control", { action });
	}

	sendChatMessage(message, options = {}) {
		if (!this.connected) throw new Error("Not connected to SFU");
		const payload = { message: String(message || "") };
		if (options.clientId) payload.clientId = String(options.clientId);
		this.socket.emit("chat:send", payload);
	}

	// Screen sharing
	sendScreenShare(action, shareData = {}) {
		if (!this.connected) {
			throw new Error("Not connected to SFU");
		}
		this.socket.emit("screen_share", { action, shareData });
	}

	// Event handler management
	on(event, handler) {
		this.eventHandlers[event] = handler;
		if (this.socket) {
			this.socket.on(event, handler);
		}
	}

	off(event) {
		delete this.eventHandlers[event];
		if (this.socket) {
			this.socket.off(event);
		}
	}

	// Utility methods
	isConnected() {
		return this.connected;
	}

	getMeetingId() {
		return this.meetingId;
	}

	getUserId() {
		return this.userId;
	}
}

// Export singleton instance
let sfuClient = null;

export function getSFUClient() {
	if (!sfuClient) {
		sfuClient = new SFUClient();
	}
	return sfuClient;
}

export function createSFUClient() {
	return new SFUClient();
}

export default getSFUClient;
