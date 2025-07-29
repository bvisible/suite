// WebRTC Manager for handling video conferencing connections
// Copyright (c) 2025, Frappe and contributors
// For license information, please see license.txt

import {
	joinMeeting,
	leaveMeeting,
	registerWebRTCEventHandlers,
	sendMediaControl,
	sendWebRTCSignal,
	unregisterWebRTCEventHandlers,
	useSocket,
} from "./socket.js";

class WebRTCManager {
	constructor() {
		this.localStream = null;
		this.remoteStreams = new Map();
		this.peerConnections = new Map();
		this.meetingId = null;
		this.isJoined = false;
		this.isMuted = false;
		this.isCameraOff = false;
		this.isScreenSharing = false;

		// WebRTC configuration
		this.rtcConfig = {
			iceServers: [
				{ urls: "stun:stun.l.google.com:19302" },
				{ urls: "stun:stun1.l.google.com:19302" },
			],
			iceCandidatePoolSize: 10,
		};

		// Event callbacks
		this.callbacks = {
			onParticipantJoined: null,
			onParticipantLeft: null,
			onRemoteStream: null,
			onLocalStream: null,
			onError: null,
			onMeetingJoined: null,
			onMeetingLeft: null,
		};

		this.setupSocketEventHandlers();
	}

	setupSocketEventHandlers() {
		const handlers = {
			onMeetingJoined: (data) => {
				this.isJoined = true;
				if (this.callbacks.onMeetingJoined) {
					this.callbacks.onMeetingJoined(data);
				}
			},

			onMeetingLeft: (data) => {
				this.isJoined = false;
				this.cleanup();
				if (this.callbacks.onMeetingLeft) {
					this.callbacks.onMeetingLeft(data);
				}
			},

			onParticipantJoined: (data) => {
				this.handleParticipantJoined(data);
			},

			onParticipantLeft: (data) => {
				this.handleParticipantLeft(data);
			},

			onWebRTCOffer: (data) => {
				this.handleWebRTCOffer(data);
			},

			onWebRTCAnswer: (data) => {
				this.handleWebRTCAnswer(data);
			},

			onICECandidate: (data) => {
				this.handleICECandidate(data);
			},

			onSFUError: (data) => {
				console.error("SFU Error:", data);
				if (this.callbacks.onError) {
					this.callbacks.onError(data);
				}
			},
		};

		registerWebRTCEventHandlers(handlers);
	}

	async initialize(meetingId) {
		try {
			this.meetingId = meetingId;

			// Get user media
			await this.getUserMedia();

			// Join the meeting
			joinMeeting(meetingId);

			return true;
		} catch (error) {
			console.error("Failed to initialize WebRTC:", error);
			if (this.callbacks.onError) {
				this.callbacks.onError(error);
			}
			return false;
		}
	}

	async getUserMedia(constraints = null) {
		try {
			const defaultConstraints = {
				video: {
					width: { ideal: 1280 },
					height: { ideal: 720 },
					frameRate: { ideal: 30 },
				},
				audio: {
					echoCancellation: true,
					noiseSuppression: true,
					autoGainControl: true,
				},
			};

			this.localStream = await navigator.mediaDevices.getUserMedia(
				constraints || defaultConstraints,
			);

			if (this.callbacks.onLocalStream) {
				this.callbacks.onLocalStream(this.localStream);
			}

			return this.localStream;
		} catch (error) {
			console.error("Failed to get user media:", error);
			throw error;
		}
	}

	async createPeerConnection(participantId) {
		const pc = new RTCPeerConnection(this.rtcConfig);

		// Add local stream tracks
		if (this.localStream) {
			for (const track of this.localStream.getTracks()) {
				pc.addTrack(track, this.localStream);
			}
		}

		// Handle remote stream
		pc.ontrack = (event) => {
			const [remoteStream] = event.streams;
			this.remoteStreams.set(participantId, remoteStream);

			if (this.callbacks.onRemoteStream) {
				this.callbacks.onRemoteStream(participantId, remoteStream);
			}
		};

		// Handle ICE candidates
		pc.onicecandidate = (event) => {
			if (event.candidate) {
				sendWebRTCSignal(
					this.meetingId,
					"ice-candidate",
					{ candidate: event.candidate },
					participantId,
				);
			}
		};

		// Handle connection state changes
		pc.onconnectionstatechange = () => {
			console.log(
				`Connection state with ${participantId}:`,
				pc.connectionState,
			);

			if (
				pc.connectionState === "failed" ||
				pc.connectionState === "disconnected"
			) {
				this.handleParticipantLeft({ participantId });
			}
		};

		this.peerConnections.set(participantId, pc);
		return pc;
	}

	async handleParticipantJoined(data) {
		const { participantId } = data;

		if (participantId === this.getCurrentUserId()) {
			return; // Don't create connection to self
		}

		try {
			const pc = await this.createPeerConnection(participantId);

			// Create and send offer
			const offer = await pc.createOffer();
			await pc.setLocalDescription(offer);

			sendWebRTCSignal(
				this.meetingId,
				"offer",
				{ offer: offer },
				participantId,
			);

			if (this.callbacks.onParticipantJoined) {
				this.callbacks.onParticipantJoined(data);
			}
		} catch (error) {
			console.error("Failed to handle participant joined:", error);
		}
	}

	async handleParticipantLeft(data) {
		const { participantId } = data;

		// Clean up peer connection
		const pc = this.peerConnections.get(participantId);
		if (pc) {
			pc.close();
			this.peerConnections.delete(participantId);
		}

		// Remove remote stream
		this.remoteStreams.delete(participantId);

		if (this.callbacks.onParticipantLeft) {
			this.callbacks.onParticipantLeft(data);
		}
	}

	async handleWebRTCOffer(data) {
		const { fromUser, signalData } = data;

		try {
			let pc = this.peerConnections.get(fromUser);
			if (!pc) {
				pc = await this.createPeerConnection(fromUser);
			}

			await pc.setRemoteDescription(signalData.offer);

			// Create and send answer
			const answer = await pc.createAnswer();
			await pc.setLocalDescription(answer);

			sendWebRTCSignal(this.meetingId, "answer", { answer: answer }, fromUser);
		} catch (error) {
			console.error("Failed to handle WebRTC offer:", error);
		}
	}

	async handleWebRTCAnswer(data) {
		const { fromUser, signalData } = data;

		try {
			const pc = this.peerConnections.get(fromUser);
			if (pc) {
				await pc.setRemoteDescription(signalData.answer);
			}
		} catch (error) {
			console.error("Failed to handle WebRTC answer:", error);
		}
	}

	async handleICECandidate(data) {
		const { fromUser, signalData } = data;

		try {
			const pc = this.peerConnections.get(fromUser);
			if (pc) {
				await pc.addIceCandidate(signalData.candidate);
			}
		} catch (error) {
			console.error("Failed to handle ICE candidate:", error);
		}
	}

	toggleMicrophone() {
		if (this.localStream) {
			const audioTrack = this.localStream.getAudioTracks()[0];
			if (audioTrack) {
				audioTrack.enabled = !audioTrack.enabled;
				this.isMuted = !audioTrack.enabled;

				// Notify other participants
				sendMediaControl(this.meetingId, this.isMuted ? "mute" : "unmute");
			}
		}
		return !this.isMuted;
	}

	toggleCamera() {
		if (this.localStream) {
			const videoTrack = this.localStream.getVideoTracks()[0];
			if (videoTrack) {
				videoTrack.enabled = !videoTrack.enabled;
				this.isCameraOff = !videoTrack.enabled;

				// Notify other participants
				sendMediaControl(
					this.meetingId,
					this.isCameraOff ? "camera_off" : "camera_on",
				);
			}
		}
		return !this.isCameraOff;
	}

	async startScreenShare() {
		try {
			const screenStream = await navigator.mediaDevices.getDisplayMedia({
				video: true,
				audio: true,
			});

			// Replace video track in all peer connections
			const videoTrack = screenStream.getVideoTracks()[0];

			for (const [participantId, pc] of this.peerConnections) {
				const sender = pc
					.getSenders()
					.find((s) => s.track && s.track.kind === "video");

				if (sender) {
					await sender.replaceTrack(videoTrack);
				}
			}

			// Handle screen share end
			videoTrack.onended = () => {
				this.stopScreenShare();
			};

			this.isScreenSharing = true;
			return screenStream;
		} catch (error) {
			console.error("Failed to start screen share:", error);
			throw error;
		}
	}

	async stopScreenShare() {
		if (this.isScreenSharing && this.localStream) {
			// Replace back to camera
			const videoTrack = this.localStream.getVideoTracks()[0];

			for (const [participantId, pc] of this.peerConnections) {
				const sender = pc
					.getSenders()
					.find((s) => s.track && s.track.kind === "video");

				if (sender) {
					await sender.replaceTrack(videoTrack);
				}
			}
		}

		this.isScreenSharing = false;
	}

	leave() {
		if (this.isJoined) {
			leaveMeeting(this.meetingId);
		}
		this.cleanup();
	}

	cleanup() {
		// Close all peer connections
		for (const [participantId, pc] of this.peerConnections) {
			pc.close();
		}
		this.peerConnections.clear();

		// Stop local stream
		if (this.localStream) {
			for (const track of this.localStream.getTracks()) {
				track.stop();
			}
			this.localStream = null;
		}

		// Clear remote streams
		this.remoteStreams.clear();

		// Reset state
		this.isJoined = false;
		this.isMuted = false;
		this.isCameraOff = false;
		this.isScreenSharing = false;
	}

	// Event callback setters
	onParticipantJoined(callback) {
		this.callbacks.onParticipantJoined = callback;
	}

	onParticipantLeft(callback) {
		this.callbacks.onParticipantLeft = callback;
	}

	onRemoteStream(callback) {
		this.callbacks.onRemoteStream = callback;
	}

	onLocalStream(callback) {
		this.callbacks.onLocalStream = callback;
	}

	onError(callback) {
		this.callbacks.onError = callback;
	}

	onMeetingJoined(callback) {
		this.callbacks.onMeetingJoined = callback;
	}

	onMeetingLeft(callback) {
		this.callbacks.onMeetingLeft = callback;
	}

	// Utility methods
	getCurrentUserId() {
		// This should return the current user ID from your auth system
		return window.frappe?.session?.user || "anonymous";
	}

	getLocalStream() {
		return this.localStream;
	}

	getRemoteStream(participantId) {
		return this.remoteStreams.get(participantId);
	}

	getConnectionState(participantId) {
		const pc = this.peerConnections.get(participantId);
		return pc ? pc.connectionState : "disconnected";
	}
}

// Export singleton instance
export const webrtcManager = new WebRTCManager();
export default webrtcManager;
