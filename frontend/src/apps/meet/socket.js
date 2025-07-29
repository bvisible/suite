import { frappeRequest } from "frappe-ui";
import { io } from "socket.io-client";
import { socketio_port } from "../../../../sites/common_site_config.json";

let socket = null;
let webrtcEventHandlers = {};

export function initSocket() {
	const host = window.location.hostname;
	const siteName = window.site_name;
	const port = window.location.port ? `:${socketio_port}` : "";
	const protocol = port ? "http" : "https";
	const url = `${protocol}://${host}${port}/${siteName}`;

	socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	});

	// Set up default video conferencing event listeners
	setupVideoConferencingListeners();

	return socket;
}

export function useSocket() {
	return socket;
}

function setupVideoConferencingListeners() {
	if (!socket) return;

	// Meeting events
	socket.on("meeting_joined_success", (data) => {
		console.log("Successfully joined meeting:", data);
		if (webrtcEventHandlers.onMeetingJoined) {
			webrtcEventHandlers.onMeetingJoined(data);
		}
	});

	socket.on("meeting_join_error", (data) => {
		console.error("Failed to join meeting:", data);
		if (webrtcEventHandlers.onMeetingJoinError) {
			webrtcEventHandlers.onMeetingJoinError(data);
		}
	});

	socket.on("meeting_left_success", (data) => {
		console.log("Successfully left meeting:", data);
		if (webrtcEventHandlers.onMeetingLeft) {
			webrtcEventHandlers.onMeetingLeft(data);
		}
	});

	socket.on("participant_joined", (data) => {
		console.log("New participant joined:", data);
		if (webrtcEventHandlers.onParticipantJoined) {
			webrtcEventHandlers.onParticipantJoined(data);
		}
	});

	socket.on("participant_left", (data) => {
		console.log("Participant left:", data);
		if (webrtcEventHandlers.onParticipantLeft) {
			webrtcEventHandlers.onParticipantLeft(data);
		}
	});

	// WebRTC signaling events
	socket.on("webrtc_offer", (data) => {
		console.log("Received WebRTC offer:", data);
		if (webrtcEventHandlers.onWebRTCOffer) {
			webrtcEventHandlers.onWebRTCOffer(data);
		}
	});

	socket.on("webrtc_answer", (data) => {
		console.log("Received WebRTC answer:", data);
		if (webrtcEventHandlers.onWebRTCAnswer) {
			webrtcEventHandlers.onWebRTCAnswer(data);
		}
	});

	socket.on("ice_candidate", (data) => {
		console.log("Received ICE candidate:", data);
		if (webrtcEventHandlers.onICECandidate) {
			webrtcEventHandlers.onICECandidate(data);
		}
	});

	// Media producer/consumer events
	socket.on("producer_created", (data) => {
		console.log("Producer created:", data);
		if (webrtcEventHandlers.onProducerCreated) {
			webrtcEventHandlers.onProducerCreated(data);
		}
	});

	socket.on("producer_closed", (data) => {
		console.log("Producer closed:", data);
		if (webrtcEventHandlers.onProducerClosed) {
			webrtcEventHandlers.onProducerClosed(data);
		}
	});

	socket.on("consumer_created", (data) => {
		console.log("Consumer created:", data);
		if (webrtcEventHandlers.onConsumerCreated) {
			webrtcEventHandlers.onConsumerCreated(data);
		}
	});

	socket.on("consumer_closed", (data) => {
		console.log("Consumer closed:", data);
		if (webrtcEventHandlers.onConsumerClosed) {
			webrtcEventHandlers.onConsumerClosed(data);
		}
	});

	// Media control events
	socket.on("media_control_update", (data) => {
		console.log("Media control update:", data);
		if (webrtcEventHandlers.onMediaControlUpdate) {
			webrtcEventHandlers.onMediaControlUpdate(data);
		}
	});

	// Screen sharing events
	socket.on("screen_share_started", (data) => {
		console.log("Screen share started:", data);
		if (webrtcEventHandlers.onScreenShareStarted) {
			webrtcEventHandlers.onScreenShareStarted(data);
		}
	});

	socket.on("screen_share_stopped", (data) => {
		console.log("Screen share stopped:", data);
		if (webrtcEventHandlers.onScreenShareStopped) {
			webrtcEventHandlers.onScreenShareStopped(data);
		}
	});

	// Chat events
	socket.on("meeting_chat_message", (data) => {
		console.log("New chat message:", data);
		if (webrtcEventHandlers.onChatMessage) {
			webrtcEventHandlers.onChatMessage(data);
		}
	});

	// Error events
	socket.on("sfu_error", (data) => {
		console.error("SFU error:", data);
		if (webrtcEventHandlers.onSFUError) {
			webrtcEventHandlers.onSFUError(data);
		}
	});

	// Router RTP capabilities - delegated to mediasoup-client
	socket.on("router_rtp_capabilities", async (data) => {
		console.log("Received router RTP capabilities:", data);
		if (webrtcEventHandlers.onRouterRTPCapabilities) {
			webrtcEventHandlers.onRouterRTPCapabilities(data);
		}
	});

	// Transport events - delegated to mediasoup-client
	socket.on("webrtc_transport_created", async (data) => {
		console.log("WebRTC transport created:", data);
		if (webrtcEventHandlers.onWebRTCTransportCreated) {
			webrtcEventHandlers.onWebRTCTransportCreated(data);
		}
	});

	socket.on("webrtc_transport_connected", (data) => {
		console.log("WebRTC transport connected:", data);
		if (webrtcEventHandlers.onWebRTCTransportConnected) {
			webrtcEventHandlers.onWebRTCTransportConnected(data);
		}
	});

	// Media events - delegated to mediasoup-client
	socket.on("media_produced", (data) => {
		console.log("Media produced:", data);
		if (webrtcEventHandlers.onMediaProduced) {
			webrtcEventHandlers.onMediaProduced(data);
		}
	});

	socket.on("media_consumed", async (data) => {
		console.log("Media consumed:", data);
		if (webrtcEventHandlers.onMediaConsumed) {
			webrtcEventHandlers.onMediaConsumed(data);
		}
	});

	socket.on("producer_paused", (data) => {
		console.log("Producer paused:", data);
		if (webrtcEventHandlers.onProducerPaused) {
			webrtcEventHandlers.onProducerPaused(data);
		}
	});

	socket.on("producer_resumed", (data) => {
		console.log("Producer resumed:", data);
		if (webrtcEventHandlers.onProducerResumed) {
			webrtcEventHandlers.onProducerResumed(data);
		}
	});

	socket.on("consumer_paused", (data) => {
		console.log("Consumer paused:", data);
		if (webrtcEventHandlers.onConsumerPaused) {
			webrtcEventHandlers.onConsumerPaused(data);
		}
	});

	socket.on("consumer_resumed", (data) => {
		console.log("Consumer resumed:", data);
		if (webrtcEventHandlers.onConsumerResumed) {
			webrtcEventHandlers.onConsumerResumed(data);
		}
	});
}

// Video conferencing utility functions
export async function joinMeeting(meetingId) {
	if (!socket) {
		throw new Error("Socket not initialized");
	}

	try {
		// First, join the socket room for real-time communication with Frappe
		socket.emit("join_meeting", { meeting_id: meetingId });

		// Join the meeting in Frappe (authentication and permission check)
		const response = await frappeRequest({
			url: "sae.api.meeting.join_meeting",
			params: { meeting_id: meetingId },
		});

		if (!response.success) {
			throw new Error(response.error || "Failed to join meeting");
		}

		console.log("✅ Successfully joined meeting in Frappe:", response);

		// Note: SFU connection will be established separately via SFUClient
		// when WebRTC operations are initiated

		return response;
	} catch (error) {
		console.error("❌ Error joining meeting:", error);
		throw error;
	}
}

export async function leaveMeeting(meetingId) {
	if (!socket) {
		throw new Error("Socket not initialized");
	}

	try {
		// First, leave the socket room
		socket.emit("leave_meeting", { meeting_id: meetingId });

		// Leave the meeting in Frappe
		const response = await frappeRequest({
			url: "sae.api.meeting.leave_meeting",
			params: { meeting_id: meetingId },
		});

		console.log("✅ Successfully left meeting in Frappe:", response);

		// Note: SFU disconnection should be handled separately via SFUClient

		return response;
	} catch (error) {
		console.error("❌ Error leaving meeting:", error);
		throw error;
	}
}

export async function sendWebRTCSignal(
	meetingId,
	signalType,
	signalData,
	targetUser = null,
) {
	if (!socket) {
		throw new Error("Socket not initialized");
	}

	try {
		// For direct peer-to-peer WebRTC signals, use socket for speed
		socket.emit("webrtc_signal", {
			meeting_id: meetingId,
			type: signalType,
			signal_data: signalData,
			target_user: targetUser,
		});

		// Note: SFU-mediated signals now go directly to SFU via SFUClient
		// These API calls are deprecated in favor of direct SFU communication
		const sfuEvents = [
			"get_router_capabilities",
			"create_transport",
			"connect_transport",
			"produce",
			"consume",
		];

		if (sfuEvents.includes(signalType)) {
			console.warn(
				`⚠️ DEPRECATED: ${signalType} should use direct SFU connection instead of relay`,
			);
			// Still support for backward compatibility but log warning
		}
	} catch (error) {
		console.error("❌ Error sending WebRTC signal:", error);
		throw error;
	}
}

export async function sendMediaControl(meetingId, action) {
	if (!socket) {
		throw new Error("Socket not initialized");
	}

	try {
		// Send through socket for immediate feedback to participants
		socket.emit("media_control", {
			meeting_id: meetingId,
			action: action,
		});

		// Also call API for SFU coordination if needed
		const response = await frappeRequest({
			url: "sae.utils.socket_handlers.handle_media_control",
			params: {
				meeting_id: meetingId,
				action: action,
			},
		});

		return response;
	} catch (error) {
		console.error("Error sending media control:", error);
		throw error;
	}
}

export async function sendScreenShare(meetingId, action, shareData = {}) {
	if (!socket) {
		throw new Error("Socket not initialized");
	}

	try {
		// Send through socket for immediate feedback
		socket.emit("screen_share", {
			meeting_id: meetingId,
			action: action,
			share_data: shareData,
		});

		// Also call API for SFU coordination if needed
		const response = await frappeRequest({
			url: "sae.utils.socket_handlers.handle_screen_share",
			params: {
				meeting_id: meetingId,
				action: action,
				share_data: shareData,
			},
		});

		return response;
	} catch (error) {
		console.error("Error sending screen share:", error);
		throw error;
	}
}

export function sendChatMessage(meetingId, message) {
	if (!socket) {
		throw new Error("Socket not initialized");
	}

	// Chat messages can be handled entirely through socket for real-time delivery
	socket.emit("chat_message", {
		meeting_id: meetingId,
		message: message,
	});
}

// Register event handlers for video conferencing
export function registerWebRTCEventHandlers(handlers) {
	webrtcEventHandlers = { ...webrtcEventHandlers, ...handlers };
}

// Remove event handlers
export function unregisterWebRTCEventHandlers() {
	webrtcEventHandlers = {};
}
