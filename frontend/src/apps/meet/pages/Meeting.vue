<template>
	<div class="h-screen bg-gray-900 flex flex-col">
		<!-- Loading state -->
		<div v-if="isConnecting" class="flex-1 flex items-center justify-center">
			<div class="text-center text-white space-y-4">
				<Spinner class="h-24 mx-auto" />
				<p class="text-lg">Joining meeting...</p>
			</div>
		</div>

		<!-- Error state -->
		<div v-else-if="connectionError" class="flex-1 flex items-center justify-center">
			<div class="text-center text-white">
				<div class="text-red-500 mb-4">
					<lucide-alert-circle class="w-12 h-12 mx-auto" />
				</div>
				<p class="text-lg mb-4">{{ connectionError }}</p>
				<Button @click="joinMeetingRoom" variant="outline" theme="red"> Try Again </Button>
			</div>
		</div>

		<!-- Main video interface -->
		<template v-else>
			<!-- Meeting info bar -->
			<div class="bg-gray-800 px-6 py-2 flex-shrink-0 border-b border-gray-700">
				<div class="flex items-center justify-between">
					<div class="text-white">
						<span
							class="text-sm cursor-pointer hover:text-gray-300 transition-colors"
							@click="copyMeetingUrl"
							:title="'Click to copy meeting URL'"
						>
							{{ meetingDoc?.data?.title || meetingId }}
						</span>
					</div>
				</div>
			</div>

			<!-- Main content area -->
			<div class="flex-1 p-4 flex flex-col min-h-0 overflow-auto">
				<!-- Screen share active view (Google Meet style) -->
				<div
					v-if="displayScreenShares.length"
					class="flex-1 flex min-h-0 overflow-hidden mb-2"
				>
					<!-- Main screen share area -->
					<div
						class="flex-1 relative bg-black rounded-lg overflow-hidden flex items-center justify-center"
					>
						<template
							v-for="(share, idx) in displayScreenShares"
							:key="share.consumerId"
						>
							<!-- Render only the first (focused) screen share. Local & remote handled uniformly -->
							<video
								v-if="idx === 0"
								:ref="setScreenShareVideoRef"
								:data-participant-id="share.participantId"
								class="w-full h-full object-contain bg-gray-900"
								autoplay
								playsinline
								muted
							></video>
						</template>
						<!-- Single label for active screen share -->
						<div class="absolute top-2 left-2">
							<span
								v-if="displayScreenShares.length"
								class="px-2 py-1 bg-black/60 text-white text-xs rounded"
								>{{ getParticipantName(displayScreenShares[0].participantId) }}'s
								screen</span
							>
						</div>
					</div>
					<!-- Sidebar tiles -->
					<TransitionGroup
						name="tile"
						tag="div"
						class="ml-3 overflow-y-auto pr-1 grid gap-2 h-full"
						:class="screenShareSidebarClass"
						:style="screenShareSidebarStyle"
					>
						<!-- Local camera tile -->
						<div
							key="local-camera-sidebar"
							class="relative w-full bg-gray-800 rounded overflow-hidden flex"
							:style="singleSidebarTileStyle"
						>
							<video
								ref="localVideo"
								class="w-full h-full object-cover transform scale-x-[-1] flex-1"
								autoplay
								muted
								playsinline
							/>
							<div
								v-if="!isCameraOn"
								class="absolute inset-0 bg-gray-700 flex items-center justify-center"
							>
								<Avatar size="3xl" :label="userInitials" :image="userAvatar" />
							</div>
							<div
								class="absolute bottom-1 left-1 text-[10px] bg-black/60 text-white px-1 rounded"
							>
								You
							</div>
						</div>
						<!-- Remote participants -->
						<div
							v-for="participant in sidebarRemotesDisplay.list"
							:key="'side-' + participant.user_id"
							class="relative w-full bg-gray-800 rounded overflow-hidden flex"
							:style="singleSidebarTileStyle"
						>
							<video
								:ref="(el) => setRemoteVideoRef(participant.user_id, el)"
								:participant-id="participant.user_id"
								class="w-full h-full object-cover flex-1"
								autoplay
								playsinline
							></video>
							<div
								v-if="!participant.video_enabled"
								class="absolute inset-0 flex items-center justify-center bg-gray-700"
							>
								<Avatar
									size="3xl"
									:image="participant.avatar"
									:label="participant.initials"
								/>
							</div>
							<div
								class="absolute bottom-1 left-1 text-[10px] bg-black/60 text-white px-1 rounded"
							>
								{{ participant.user_name }}
							</div>
							<div
								v-if="!participant.audio_enabled"
								class="absolute top-1 right-1 bg-gray-700 rounded-full p-1"
							>
								<lucide-mic-off class="w-3 h-3 text-white" />
							</div>
						</div>
						<!-- Grouping tile -->
						<Tooltip
							v-if="sidebarRemotesDisplay.extra > 0"
							key="sidebar-group"
							:label="hiddenParticipantsTooltip"
							:text="hiddenParticipantsTooltip"
							placement="top"
						>
							<div
								class="relative w-full bg-gray-800/70 rounded overflow-hidden flex items-center justify-center cursor-pointer"
							>
								<div class="text-xs text-white text-center px-2 leading-snug">
									and {{ sidebarRemotesDisplay.extra }} others
								</div>
							</div>
						</Tooltip>
					</TransitionGroup>
				</div>

				<!-- Video grid (hidden when screen sharing) -->
				<TransitionGroup
					v-else
					name="tile"
					tag="div"
					class="flex-1 grid gap-2 min-h-0 call-grid"
					:class="gridClass"
					:style="callGridStyle"
				>
					<!-- Local user video -->
					<div
						key="local-camera"
						class="relative bg-gray-800 rounded-lg overflow-hidden min-h-0"
					>
						<video
							ref="localVideo"
							class="w-full h-full object-cover transform scale-x-[-1]"
							autoplay
							muted
							playsinline
						/>
						<div
							class="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-sm z-20 pointer-events-none"
						>
							{{ currentUser?.full_name || currentUser?.name || "You" }}
						</div>
						<div
							v-if="!isCameraOn"
							class="absolute inset-0 bg-gray-700 flex items-center justify-center z-10 pointer-events-none"
						>
							<Avatar size="3xl" :label="userInitials" :image="userAvatar" />
						</div>
					</div>

					<!-- Remote participants -->
					<div
						v-for="participant in gridRemotesDisplay.list"
						:key="'grid-' + participant.user_id"
						class="relative bg-gray-800 rounded-lg overflow-hidden min-h-0"
					>
						<video
							:ref="(el) => setRemoteVideoRef(participant.user_id, el)"
							:participant-id="participant.user_id"
							class="w-full h-full object-cover"
							autoplay
							playsinline
						></video>
						<div
							class="absolute bottom-2 left-2 bg-black bg-opacity-50 text-white px-2 py-1 rounded text-sm z-20 pointer-events-none"
						>
							{{ participant.user_name || participant.user_id }}
						</div>
						<div
							v-if="!participant.video_enabled"
							class="absolute inset-0 bg-gray-700 flex items-center justify-center z-10 pointer-events-none"
						>
							<Avatar
								size="3xl"
								:image="participant.avatar"
								:label="participant.initials"
							/>
						</div>
						<div
							v-if="!participant.audio_enabled"
							class="absolute top-2 right-2 bg-gray-700 rounded-full p-1.5"
						>
							<lucide-mic-off class="w-4 h-4 text-white" />
						</div>
					</div>
					<!-- Grouping tile for normal layout -->
					<Tooltip
						v-if="gridRemotesDisplay.extra > 0"
						key="grid-group"
						:label="hiddenGridParticipantsTooltip"
						:text="hiddenGridParticipantsTooltip"
						placement="top"
					>
						<div
							class="relative bg-gray-800/70 rounded-lg overflow-hidden min-h-0 flex items-center justify-center cursor-pointer"
						>
							<div class="text-sm text-white text-center px-3 leading-snug">
								and {{ gridRemotesDisplay.extra }} others
							</div>
						</div>
					</Tooltip>
				</TransitionGroup>
			</div>

			<!-- Bottom controls -->
			<div class="bg-gray-800 px-6 py-4 flex-shrink-0">
				<div class="flex items-center justify-center">
					<!-- Main controls -->
					<div class="flex items-center space-x-6">
						<!-- Microphone -->
						<Button
							@click="toggleMicrophone"
							:variant="isMicOn ? 'solid' : 'solid'"
							:theme="isMicOn ? 'gray' : 'red'"
							size="lg"
							class="w-12 h-12 rounded-full p-0"
							:title="
								'Toggle Audio (' + ($platform === 'mac' ? '⌘+D' : 'Ctrl+D') + ')'
							"
						>
							<template #icon>
								<lucide-mic-off v-if="!isMicOn" class="w-6 h-6 text-white" />
								<lucide-mic v-else class="w-6 h-6 text-white" />
							</template>
						</Button>

						<!-- Camera -->
						<Button
							@click="toggleCamera"
							:variant="isCameraOn ? 'solid' : 'solid'"
							:theme="isCameraOn ? 'gray' : 'red'"
							size="lg"
							class="w-12 h-12 rounded-full p-0"
							:title="
								'Toggle Video (' + ($platform === 'mac' ? '⌘+E' : 'Ctrl+E') + ')'
							"
						>
							<template #icon>
								<lucide-video-off v-if="!isCameraOn" class="w-6 h-6 text-white" />
								<lucide-video v-else class="w-6 h-6 text-white" />
							</template>
						</Button>

						<!-- Screen Share -->
						<Button
							@click="toggleScreenShare"
							:variant="isScreenSharing ? 'solid' : 'solid'"
							:theme="isScreenSharing ? 'red' : 'gray'"
							size="lg"
							class="w-12 h-12 rounded-full p-0"
							title="Toggle Screen Share"
						>
							<template #icon>
								<lucide-monitor-up
									v-if="!isScreenSharing"
									class="w-6 h-6 text-white"
								/>
								<lucide-monitor-pause v-else class="w-6 h-6 text-white" />
							</template>
						</Button>

						<!-- End call -->
						<Button
							@click="endCall"
							variant="solid"
							size="lg"
							theme="red"
							class="w-12 h-12 rounded-full p-0"
							title="End Call"
						>
							<template #icon>
								<lucide-phone-off class="w-6 h-6 text-white" />
							</template>
						</Button>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup>
import {
	cameraEnabled as prefCameraEnabled,
	micEnabled as prefMicEnabled,
} from "@/data/mediaPreferences.js";
import {
	Avatar,
	Button,
	Spinner,
	Tooltip,
	getCachedDocumentResource,
	toast,
} from "frappe-ui";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { session } from "../data/session.js";
import { cleanupMediasoup } from "../mediasoup-client.js";
import { publishScreenShare } from "../mediasoup-client.js";
import {
	joinMeeting,
	leaveMeeting,
	unregisterWebRTCEventHandlers,
} from "../socket.js";
import { getSFUClient } from "../utils/sfu-client.js";
import {
	getSFUMeetingManager,
	resetSFUMeetingManager,
} from "../utils/sfu-meeting-manager.js";

// Router access
const route = useRoute();
const router = useRouter();
const meetingId = computed(() => route.params.meetingId);

// Reactive state
// Initialize mic/camera from saved preview preferences
const isMicOn = ref(prefMicEnabled.value);
const isCameraOn = ref(prefCameraEnabled.value);
const isScreenSharing = ref(false);
const screenShareStream = ref(null);
const activeScreenShareConsumers = ref([]); // list of { participantId, consumerId, startedAt }
const localScreenShareStartedAt = ref(0);
const screenShareVideoElements = new Map();
const screenShareStreams = ref(new Map()); // participantId -> MediaStream

const attachScreenStreamIfReady = (participantId) => {
	const el = screenShareVideoElements.get(participantId);
	const stream = screenShareStreams.value.get(participantId);
	if (el && stream) {
		console.log("🔗 Attaching screen stream", {
			participantId,
			track: stream.getVideoTracks()[0]?.id,
		});
		if (el.srcObject !== stream) {
			el.srcObject = stream;
			el.play?.().catch(() => {});
		}
	}
};

const setScreenShareVideoRef = (el) => {
	if (!el) return;
	const participantId = el.dataset?.participantId;
	if (participantId) {
		screenShareVideoElements.set(participantId, el);
		console.log("📺 Screen share video element set", { participantId });
		attachScreenStreamIfReady(participantId);
	}
};

// Display logic: pick the single most recently started share (remote or local)
const displayScreenShares = computed(() => {
	let latest = null;
	for (const share of activeScreenShareConsumers.value) {
		if (!latest || (share.startedAt || 0) > (latest.startedAt || 0)) {
			latest = share;
		}
	}
	if (isScreenSharing.value && currentUser.value?.user_id) {
		const localEntry = {
			participantId: currentUser.value.user_id,
			consumerId: "local-screen",
			local: true,
			startedAt: localScreenShareStartedAt.value || 0,
		};
		if (!latest || localEntry.startedAt >= (latest.startedAt || 0)) {
			latest = localEntry;
		}
	}
	return latest ? [latest] : [];
});

function getParticipantName(pid) {
	const p = participants.value.get(pid);
	return p?.user_name || pid;
}
const localVideo = ref(null);
const isConnecting = ref(true);
const connectionError = ref(null);

let currentUser = ref({});
let participants = ref(new Map());
const remoteVideos = ref(new Map());

function setRemoteVideoRef(participantId, el) {
	if (!el) return;
	if (!remoteVideos.value || !(remoteVideos.value instanceof Map)) {
		remoteVideos.value = new Map();
	}
	remoteVideos.value.set(participantId, el);
	// If participant has an already attached combined stream (camera) reuse it immediately.
	try {
		const p = participants.value.get(participantId);
		if (p?.videoStream && !el.srcObject) {
			el.srcObject = p.videoStream;
			el.play?.().catch(() => {});
			console.log(
				"🔄 Rebound existing camera stream to new element after layout change",
				{
					participantId,
				},
			);
		}
	} catch (_) {}
}

// MediaSoup state
let localStream = null;
let videoProducer = null;
let audioProducer = null;
let screenProducer = null;
const consumers = ref(new Map());

// SFU Meeting Manager
let sfuManager = null;

// Computed grid class based on participant count
const gridClass = computed(() => {
	const totalVisibleTiles =
		1 + // local
		gridRemotesDisplay.value.list.length +
		(gridRemotesDisplay.value.extra > 0 ? 1 : 0); // grouped tile if present
	let cols;
	if (totalVisibleTiles <= 1) cols = 1;
	else if (totalVisibleTiles === 2) cols = 2;
	else if (totalVisibleTiles <= 4)
		cols = 2; // 2x2
	else if (totalVisibleTiles <= 9)
		cols = 3; // up to 3x3
	else cols = 4; // 4 columns for 10+ (capped at 4x4 with grouping)
	return `grid-cols-${cols}`;
});

// Enforce equal row heights and explicit column template.
const callGridStyle = computed(() => {
	const totalVisibleTiles =
		1 +
		gridRemotesDisplay.value.list.length +
		(gridRemotesDisplay.value.extra > 0 ? 1 : 0);
	let cols;
	if (totalVisibleTiles <= 1) cols = 1;
	else if (totalVisibleTiles === 2) cols = 2;
	else if (totalVisibleTiles <= 4) cols = 2;
	else if (totalVisibleTiles <= 9) cols = 3;
	else cols = 4;
	return {
		"grid-auto-rows": "1fr",
		"grid-template-columns": `repeat(${cols}, minmax(0, 1fr))`,
	};
});

const userInitials = computed(() => {
	const name = currentUser.value.full_name || currentUser.value.name || "You";
	return name
		.split(" ")
		.map((n) => n[0])
		.join("")
		.toUpperCase()
		.slice(0, 2);
});
const userAvatar = computed(() => currentUser.value.avatar || "");

// Normal grid logic: cap visible tiles at 16 (4x4); extra participants are grouped.
const gridRemotesDisplay = computed(() => {
	const remotes = Array.from(participants.value.values());
	const total = remotes.length + 1; // include local
	const threshold = 16; // point at which grouping activates
	if (total <= threshold) {
		return { list: remotes, hidden: [], extra: 0 };
	}
	const remoteCapacity = 14; // because: 1 local + 14 remotes + 1 group tile = 16
	const videoOn = remotes.filter((p) => p.video_enabled);
	const videoOff = remotes.filter((p) => !p.video_enabled);
	const visibleRemotes = [];
	// Fill with as many video-on as possible up to capacity
	for (const p of videoOn) {
		if (visibleRemotes.length < remoteCapacity) visibleRemotes.push(p);
		else break;
	}
	// If capacity not filled, add video-off participants
	if (visibleRemotes.length < remoteCapacity) {
		for (const p of videoOff) {
			if (visibleRemotes.length < remoteCapacity) visibleRemotes.push(p);
			else break;
		}
	}
	// Hidden are all remaining not in visibleRemotes
	const visibleIds = new Set(visibleRemotes.map((p) => p.user_id));
	const hidden = remotes.filter((p) => !visibleIds.has(p.user_id));
	return { list: visibleRemotes, hidden, extra: hidden.length };
});

// Tooltip for grouped remotes in normal layout
const hiddenGridParticipantsTooltip = computed(() => {
	const hidden = gridRemotesDisplay.value.hidden || [];
	if (!hidden.length) return "";
	const names = hidden.map((p) => p.user_name || p.user_id);
	const shown = names.slice(0, 8);
	const remaining = names.length - shown.length;
	if (remaining > 0) {
		return `${shown.join(", ")} and ${remaining} more`;
	}
	if (shown.length === 1) return shown[0];
	if (shown.length === 2) return `${shown[0]} and ${shown[1]}`;
	return `${shown.slice(0, -1).join(", ")} and ${shown[shown.length - 1]}`;
});

// Screen share sidebar display logic (two-column when >4, group when >8 total including self)
const sidebarRemotesDisplay = computed(() => {
	const remotes = Array.from(participants.value.values());
	const total = remotes.length + 1; // include local user
	if (total <= 8) {
		return { list: remotes, hidden: [], extra: 0 };
	}
	// Prioritize participants with video enabled so they are never grouped.
	const videoOn = remotes.filter((p) => p.video_enabled);
	const videoOff = remotes.filter((p) => !p.video_enabled);

	const baseCapacity = 6;
	const capacity = Math.max(baseCapacity, videoOn.length);
	const visibleRemotes = [
		...videoOn,
		...videoOff.slice(0, Math.max(0, capacity - videoOn.length)),
	];
	const hidden = videoOff.slice(Math.max(0, capacity - videoOn.length));
	return { list: visibleRemotes, hidden, extra: hidden.length };
});

const screenShareSidebarClass = computed(() => {
	const total = participants.value.size + 1;
	const base = total > 4 ? "w-72 grid-cols-2" : "w-64 grid-cols-1";
	// Determine number of visible tiles including local + remotes + group tile
	const visible =
		1 +
		sidebarRemotesDisplay.value.list.length +
		(sidebarRemotesDisplay.value.extra > 0 ? 1 : 0);

	const columns = total > 4 ? 2 : 1;
	const rows = Math.ceil(visible / columns);
	return `${base} grid-rows-${rows}`;
});

const screenShareSidebarStyle = computed(() => {
	const total = participants.value.size + 1;
	const columns = total > 4 ? 2 : 1;
	const visible =
		1 +
		sidebarRemotesDisplay.value.list.length +
		(sidebarRemotesDisplay.value.extra > 0 ? 1 : 0);
	const rows = Math.ceil(visible / columns);
	// subtract total vertical gaps (rows-1)*0.5rem (gap-2 = 0.5rem) from 100%
	const gapRem = 0.5;
	const gapTotal = (rows - 1) * gapRem;

	// if only 2/3 users cap it to 25%
	if (columns === 1 && visible <= 4) {
		return {
			display: "grid",
			"grid-auto-rows": "25%",
		};
	}

	return {
		display: "grid",
		"grid-auto-rows":
			rows === 1 ? undefined : `calc((100% - ${gapTotal}rem) / ${rows})`,
	};
});

const singleSidebarTileStyle = computed(() => {
	const totalSidebarTiles =
		1 +
		sidebarRemotesDisplay.value.list.length +
		(sidebarRemotesDisplay.value.extra > 0 ? 1 : 0);
	if (totalSidebarTiles === 1) {
		return { maxHeight: "25%", height: "auto" };
	}
	return {};
});

const hiddenParticipantsTooltip = computed(() => {
	const hidden = sidebarRemotesDisplay.value.hidden || [];
	if (!hidden.length) return "";
	const names = hidden.map((p) => p.user_name || p.user_id);
	const shown = names.slice(0, 5);
	const remaining = names.length - shown.length;
	if (remaining > 0) {
		return `${shown.join(", ")} and ${remaining} more`;
	}
	if (shown.length === 1) return shown[0];
	if (shown.length === 2) return `${shown[0]} and ${shown[1]}`;
	return `${shown.slice(0, -1).join(", ")} and ${shown[shown.length - 1]}`;
});

const meetingDoc = getCachedDocumentResource("Sae Meeting", meetingId.value);

// Control functions
const toggleMicrophone = async () => {
	try {
		if (isMicOn.value) {
			if (audioProducer) {
				try {
					await audioProducer.pause();
				} catch (e) {
					console.warn("Failed to pause audio producer:", e);
				}
			}
			try {
				getSFUClient().sendMediaControl("mute");
			} catch (e) {
				console.warn(
					"Failed to send media control (audio off)",
					e?.message || e,
				);
			}
			isMicOn.value = false;
		} else {
			let needNewProducer = false;
			if (localStream) {
				for (const track of localStream.getAudioTracks()) {
					if (track.readyState === "ended") localStream.removeTrack(track);
				}
			}
			if (!localStream || localStream.getAudioTracks().length === 0) {
				try {
					const audioStream = await navigator.mediaDevices.getUserMedia({
						audio: true,
					});
					const newTrack = audioStream.getAudioTracks()[0];
					newTrack.enabled = true;
					if (!localStream) localStream = new MediaStream();
					localStream.addTrack(newTrack);
					if (audioProducer) {
						try {
							await audioProducer.close();
						} catch (e) {}
						audioProducer = null;
					}
					if (sfuManager) {
						const results = await sfuManager.publishMedia(localStream, {
							publishAudio: true,
							publishVideo: false,
						});
						audioProducer = results.audioProducer;
					}
					needNewProducer = true;
				} catch (err) {
					console.error("Error reacquiring microphone:", err);
					toast.error("Could not access microphone");
				}
			} else {
				for (const track of localStream.getAudioTracks()) {
					track.enabled = true;
				}
			}
			if (!needNewProducer && audioProducer) {
				try {
					await audioProducer.resume();
				} catch (e) {
					console.warn("Failed to resume audio producer:", e);
				}
			}
			try {
				getSFUClient().sendMediaControl("unmute");
			} catch (e) {
				console.warn(
					"Failed to send media control (audio on)",
					e?.message || e,
				);
			}
			isMicOn.value = true;
		}
	} catch (error) {
		console.error("Error toggling microphone:", error);
	}
};

const toggleCamera = async () => {
	try {
		if (isCameraOn.value) {
			if (videoProducer) {
				try {
					await videoProducer.pause();
					console.log("🛑 Paused camera video producer", videoProducer.id);
				} catch (e) {
					console.warn("Failed to pause video producer:", e);
				}
			}
			try {
				getSFUClient().sendMediaControl("video_off");
			} catch (e) {
				console.warn(
					"Failed to send media control (video off)",
					e?.message || e,
				);
			}
			isCameraOn.value = false;
		} else {
			let needNewProducer = false;
			if (localStream) {
				for (const track of localStream.getVideoTracks()) {
					if (track.readyState === "ended") localStream.removeTrack(track);
				}
			}
			if (!localStream || localStream.getVideoTracks().length === 0) {
				try {
					const videoStream = await navigator.mediaDevices.getUserMedia({
						video: true,
					});
					const newTrack = videoStream.getVideoTracks()[0];
					newTrack.enabled = true;
					if (!localStream) localStream = new MediaStream();
					localStream.addTrack(newTrack);
					if (videoProducer) {
						try {
							await videoProducer.close();
						} catch (e) {}
						videoProducer = null;
					}
					if (sfuManager) {
						const results = await sfuManager.publishMedia(localStream, {
							publishVideo: true,
							publishAudio: false,
						});
						videoProducer = results.videoProducer;
					}
					needNewProducer = true;
				} catch (err) {
					console.error("Error reacquiring camera:", err);
					toast.error("Could not access camera");
				}
			} else {
				for (const track of localStream.getVideoTracks()) {
					track.enabled = true;
				}
			}
			if (!needNewProducer && videoProducer) {
				try {
					await videoProducer.resume();
					console.log("▶️ Resumed camera video producer", videoProducer.id);
				} catch (e) {
					console.warn("Failed to resume video producer:", e);
				}
			}
			try {
				getSFUClient().sendMediaControl("video_on");
			} catch (e) {
				console.warn(
					"Failed to send media control (video on)",
					e?.message || e,
				);
			}
			isCameraOn.value = true;
		}
	} catch (error) {
		console.error("Error toggling camera:", error);
	}
};

const endCall = async () => {
	try {
		// Leave the meeting
		await leaveMeeting(meetingId.value);

		// Clean up mediasoup resources
		cleanupMediasoup();

		// Clean up local media
		if (localStream) {
			for (const track of localStream.getTracks()) {
				track.stop();
			}
		}

		// Navigate back to home
		router.push({ name: "Home" });
	} catch (error) {
		console.error("Error ending call:", error);
		// Still navigate away even if there's an error
		router.push({ name: "Home" });
	}
};

const copyMeetingUrl = async () => {
	try {
		const meetingUrl = window.location.href;
		await navigator.clipboard.writeText(meetingUrl);
		console.log("Meeting URL copied to clipboard:", meetingUrl);
	} catch (error) {
		console.error("Failed to copy meeting URL:", error);
	}
};

const initializeCamera = async () => {
	try {
		if (!isMicOn.value && !isCameraOn.value) {
			console.log(
				"Skipping initial getUserMedia (both mic & camera disabled by user)",
			);
			localStream = null; // Will be acquired lazily when user enables
			return;
		}
		console.log("Initializing media with preferences", {
			audio: isMicOn.value,
			video: isCameraOn.value,
		});
		const constraints = {};
		if (isCameraOn.value) {
			constraints.video = {
				width: { ideal: 1280 },
				height: { ideal: 720 },
				frameRate: { ideal: 30 },
			};
		}
		if (isMicOn.value) {
			constraints.audio = {
				echoCancellation: true,
				noiseSuppression: true,
				autoGainControl: true,
			};
		}
		localStream = await navigator.mediaDevices.getUserMedia(constraints);

		console.log("Media stream obtained:", localStream);

		// Wait for the next tick to ensure the video element is ready
		await new Promise((resolve) => setTimeout(resolve, 100));

		if (localVideo.value) {
			localVideo.value.srcObject = localStream;
			console.log("Local video stream assigned to video element");

			// Ensure the video plays
			try {
				await localVideo.value.play();
				console.log("Local video started playing");
			} catch (playError) {
				console.warn(
					"Auto-play failed, but video should still work:",
					playError,
				);
			}
		}
	} catch (error) {
		console.error("Error accessing camera:", error);
		isCameraOn.value = false;
		connectionError.value = "Failed to access camera and microphone";
	}
};

const joinMeetingRoom = async () => {
	try {
		isConnecting.value = true;
		connectionError.value = null;

		// Get current user info from session
		if (!session.isLoggedIn) {
			throw new Error("User not logged in");
		}

		currentUser.value = {
			user_id: session.user.sessionUser,
			name: session.user.full_name,
			full_name: session.user.full_name,
			avatar: session.user.avatar,
		};
		// Ensure currentUser is always a ref object with a value property
		if (
			!currentUser ||
			typeof currentUser !== "object" ||
			!("value" in currentUser)
		) {
			currentUser = ref(currentUser);
		}
		// Ensure participants is always a ref object with a value property
		if (
			!participants ||
			typeof participants !== "object" ||
			!("value" in participants)
		) {
			participants = ref(new Map());
		}

		// Initialize camera/audio first to show local stream
		await initializeCamera();

		// Step 1: Join the meeting in Frappe (authentication and permissions)
		const joinResult = await joinMeeting(meetingId.value);

		// Step 2: Connect directly to SFU for WebRTC operations
		sfuManager = getSFUMeetingManager();
		sfuManager.initialize({
			meetingId: meetingId.value,
			currentUser,
			participants,
			consumers,
			remoteVideos,
			eventHandlers: {
				onParticipantJoined: (participant) => {
					const name =
						participant?.user_name || participant?.user_id || "Participant";
					toast.success(`${name} joined`);
				},
				onParticipantLeft: (data) => {
					const name =
						data?.user_name ||
						data?.user_id ||
						data.participantId ||
						"Participant";
					toast.success(`${name} left`);
				},
				onConsumerCreated: (consumer, data) => {
					console.log("📋 SFU consumer created handler:", consumer, data);
				},
				onSubscriptionError: (error, data) => {
					console.error("📋 SFU subscription error handler:", error, data);
				},
				onProducerClosed: (data) => {
					console.log("📋 SFU producer closed handler:", data);
				},
				onMediaControlUpdate: (data, participant) => {
					console.log(
						"📋 SFU media control update handler:",
						data,
						participant,
					);
				},
				onScreenShareStarted: (data) => {
					console.log("📋 SFU screen share started handler:", data);
				},
				onScreenShareStopped: (data) => {
					console.log("📋 SFU screen share stopped handler:", data);
					// Remove any consumers belonging to participant if we had them marked screen
					activeScreenShareConsumers.value =
						activeScreenShareConsumers.value.filter(
							(c) => c.participantId !== data.participantId,
						);
				},
				onScreenShareProducerAdded: ({
					participantId,
					consumerId,
					consumer,
				}) => {
					if (consumer?.track) {
						const ms = new MediaStream([consumer.track]);
						screenShareStreams.value.set(participantId, ms);
						attachScreenStreamIfReady(participantId);
					}
					if (
						!activeScreenShareConsumers.value.find(
							(c) => c.consumerId === consumerId,
						)
					) {
						activeScreenShareConsumers.value = [
							...activeScreenShareConsumers.value,
							{ participantId, consumerId, startedAt: Date.now() },
						];
					}
				},
				onScreenShareProducerRemoved: ({ participantId }) => {
					activeScreenShareConsumers.value =
						activeScreenShareConsumers.value.filter(
							(c) => c.participantId !== participantId,
						);
					const el = screenShareVideoElements.get(participantId);
					if (el?.srcObject) {
						try {
							for (const t of el.srcObject.getTracks()) t.stop();
						} catch (_) {}
						el.srcObject = null;
					}
					screenShareStreams.value.delete(participantId);
				},
			},
		});
		await sfuManager.connect();

		// Hide loading indicator once we've joined
		isConnecting.value = false;

		// Step 3: Initialize mediasoup device with router capabilities from SFU
		try {
			const initPromise = sfuManager.initializeDevice();
			const timeoutPromise = new Promise((resolve) =>
				setTimeout(resolve, 3000),
			);
			const result = await Promise.race([initPromise, timeoutPromise]);
			if (result === undefined) {
				console.warn(
					"⏳ Device initialization took too long, continuing; will lazy-load on publish",
				);
			}
		} catch (devErr) {
			console.warn(
				"⚠️ Device initialization error (will continue):",
				devErr?.message || devErr,
			);
		}

		// Step 4: Start publishing media if we have local stream
		if (localStream && sfuManager) {
			const publishOptions = {
				publishVideo: isCameraOn.value,
				publishAudio: isMicOn.value,
			};
			try {
				const mediaResults = await sfuManager.publishMedia(
					localStream,
					publishOptions,
				);
				videoProducer = mediaResults.videoProducer;
				audioProducer = mediaResults.audioProducer;
			} catch (pubErr) {
				console.error("❌ publishMedia failed", pubErr);
			}
		} else {
			console.warn("⚠️ Skipping publish: localStream or sfuManager missing", {
				hasStream: !!localStream,
				hasManager: !!sfuManager,
			});
		}

		// Step 5: Request existing participants and their media streams
		// This will create receive transport on-demand when needed
		await requestExistingParticipants();

		console.log("🎉 Meeting join complete - using direct SFU architecture");
	} catch (error) {
		console.error("❌ Error joining meeting:", error);
		connectionError.value = error.message || "Failed to join meeting";
		isConnecting.value = false;
	}
};

const requestExistingParticipants = async () => {
	try {
		console.log("Requesting existing participants and their streams...");

		await sfuManager.setupExistingParticipants();
	} catch (error) {
		console.error("Error requesting existing participants:", error);
	}
};

const handleKeyDown = (event) => {
	if ((event.metaKey || event.ctrlKey) && event.key === "d") {
		event.preventDefault();
		toggleMicrophone();
	}
	if ((event.metaKey || event.ctrlKey) && event.key === "e") {
		event.preventDefault();
		toggleCamera();
	}
};

onMounted(async () => {
	window.addEventListener("keydown", handleKeyDown);

	// Join the meeting room
	await joinMeetingRoom();
});

// Watch for localVideo element and localStream to ensure they connect
watch(
	[localVideo, () => localStream],
	async ([videoElement, stream]) => {
		if (videoElement && stream && !videoElement.srcObject) {
			console.log("Connecting local stream to video element");
			videoElement.srcObject = stream;
			try {
				await videoElement.play();
			} catch (error) {
				console.warn("Auto-play failed for local video:", error.message);
				// Local video autoplay failure is less critical since user can see themselves
			}
		}
	},
	{ immediate: true },
);

onUnmounted(async () => {
	// Clean up WebRTC event handlers
	unregisterWebRTCEventHandlers();

	// Clean up SFU manager
	if (sfuManager) {
		sfuManager.cleanup();
	}

	// Reset SFU manager instance
	resetSFUMeetingManager();

	// Always reset participants to a ref with a Map after cleanup
	participants.value = new Map();

	// Leave meeting in Frappe
	try {
		await leaveMeeting(meetingId.value);
	} catch (error) {
		console.error("❌ Error leaving meeting:", error);
	}

	// Clean up mediasoup resources
	cleanupMediasoup();

	// Stop screen share if active
	try {
		if (screenProducer) await screenProducer.close();
	} catch (_) {}
	if (screenShareStream.value) {
		for (const track of screenShareStream.value.getTracks()) track.stop();
	}

	// Clean up media streams
	if (localStream) {
		for (const track of localStream.getTracks()) {
			track.stop();
		}
	}

	window.removeEventListener("keydown", handleKeyDown);
});

// Screen share toggle
const toggleScreenShare = async () => {
	if (isScreenSharing.value) {
		// Stop
		try {
			if (screenProducer) {
				await getSFUClient()
					.closeProducer?.(screenProducer.id)
					.catch(() => {});
				try {
					screenProducer.close();
				} catch (_) {}
				screenProducer = null;
			}
			getSFUClient().sendScreenShare("stop_share");
		} catch (e) {
			console.warn("Error stopping screen share", e);
		}
		try {
			if (screenShareStream.value) {
				for (const t of screenShareStream.value.getTracks()) t.stop();
			}
		} catch (_) {}
		screenShareStream.value = null;
		isScreenSharing.value = false;
		return;
	}

	// Start
	try {
		const displayStream = await navigator.mediaDevices.getDisplayMedia({
			video: { frameRate: 15 },
			audio: false,
		});
		screenShareStream.value = displayStream;
		// When user stops from system UI
		displayStream.getVideoTracks()[0].addEventListener("ended", () => {
			if (isScreenSharing.value) toggleScreenShare();
		});
		// Publish
		if (sfuManager) {
			try {
				// Reuse existing send transport via publishScreenShare helper
				screenProducer = await publishScreenShare(
					meetingId.value,
					displayStream,
				);
			} catch (e) {
				console.error("Failed to publish screen share", e);
				toast.error("Failed to share screen");
				return;
			}
		}
		try {
			getSFUClient().sendScreenShare("start_share", {});
		} catch (e) {
			console.warn("Failed to send start_share signal", e);
		}
		isScreenSharing.value = true;
		localScreenShareStartedAt.value = Date.now();

		// Register local screen share stream for unified handling
		if (currentUser.value?.user_id) {
			const pid = currentUser.value.user_id;
			screenShareStreams.value.set(pid, displayStream);
			// Ensure attachment after DOM update
			await nextTick();
			attachScreenStreamIfReady(pid);
		}
	} catch (err) {
		console.error("Screen share error", err);
		toast.error("Screen share cancelled or failed");
	}
};
</script>

<!-- these are for transition when a user joins/leaves -->
<style scoped>
.tile-enter-from,
.tile-leave-to {
	opacity: 0;
	transform: scale(0.85) translateY(8px);
}
.tile-enter-active,
.tile-leave-active {
	transition:
		opacity 180ms ease,
		transform 180ms ease;
}
.tile-move {
	transition: transform 200ms ease;
}
/* Prevent layout jump when leaving */
.tile-leave-active {
	position: relative;
}
</style>
