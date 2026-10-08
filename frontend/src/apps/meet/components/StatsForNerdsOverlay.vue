<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
<template>
	<section
		class="absolute right-2 top-2.5 z-[55] flex max-h-[calc(100%-1.25rem)] w-[calc(100%-1rem)] max-w-[380px] flex-col overflow-hidden rounded-[10px] border border-outline-gray-2 bg-surface-gray-1 text-ink-gray-8 shadow-xl"
		:aria-label="__('Stats for nerds')"
		data-testid="stats-for-nerds"
	>
		<header class="flex shrink-0 items-center justify-between gap-3 p-4">
			<div class="flex min-w-0 items-center gap-2.5">
				<span
					class="size-2.5 shrink-0 rounded-full"
					:class="qualityDot"
				/>
				<div class="min-w-0">
					<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
					<h2 class="truncate text-sm-medium tracking-[0.21px] text-ink-gray-8">{{ __('Stats for nerds') }}</h2>
					<!-- //// Neoffice — i18n: a whole translated sentence per quality (qualityLabel below), no `capitalize` (it would read "Bonne Connexion") (#1316) -->
					<p class="text-xs text-ink-gray-5">{{ qualityLabel }}</p>
				</div>
			</div>
			<div class="flex items-center gap-1">
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<Tooltip :text="__('Copy diagnostics')">
					<button class="rounded-4 p-1.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8" :aria-label="__('Copy diagnostics')" @click="copyDiagnostics">
						<LucideCopy class="size-4" />
					</button>
				</Tooltip>
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<Tooltip :text="expanded ? __('Show less') : __('Show more')">
					<button class="rounded-4 p-1.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8" :aria-label="expanded ? __('Show less') : __('Show more')" @click="expanded = !expanded">
						<LucideChevronUp v-if="expanded" class="size-4" />
						<LucideChevronDown v-else class="size-4" />
					</button>
				</Tooltip>
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<Tooltip :text="__('Close')">
					<button class="rounded-4 p-1.5 text-ink-gray-5 hover:bg-surface-gray-2 hover:text-ink-gray-8" :aria-label="__('Close')" @click="close">
						<LucideX class="size-4" />
					</button>
				</Tooltip>
			</div>
		</header>

		<div class="overflow-y-auto px-4 pb-4 text-xs">
			<div class="grid grid-cols-2 gap-x-5 gap-y-2">
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<StatValue :label="__('Round-trip time')" :value="formatMs(snapshot.rtt)" />
				<StatValue :label="__('Jitter')" :value="formatMs(snapshot.jitter)" />
				<StatValue :label="__('Packet loss in')" :value="formatPercent(snapshot.inboundPacketLoss)" />
				<StatValue :label="__('Packet loss out')" :value="formatPercent(snapshot.outboundPacketLoss)" />
				<StatValue :label="__('Download')" :value="formatBitrate(snapshot.downloadBitrate)" />
				<StatValue :label="__('Upload')" :value="formatBitrate(snapshot.uploadBitrate)" />
				<StatValue :label="__('Available upload')" :value="formatBitrate(snapshot.availableOutgoingBitrate)" />
				<StatValue :label="__('Lifecycle')" :value="humanize(participantConnectionState.lifecycleState)" />
			</div>

			<template v-if="expanded">
				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<StatsSection :title="__('Connection')">
					<StatsRow :label="__('Signaling')" :value="connectionStatus" />
					<StatsRow :label="__('Send transport')" :value="transportStates.send" />
					<StatsRow :label="__('Receive transport')" :value="transportStates.receive" />
					<StatsRow :label="__('ICE route')" :value="iceRoute" />
					<StatsRow :label="__('Protocol')" :value="snapshot.protocol?.toUpperCase() || __('n/a')" />
					<StatsRow :label="__('Encoding strategy')" :value="connectionState.codecStrategy?.toUpperCase() || __('n/a')" />
					<StatsRow :label="__('Encryption')" :value="encryptionStatus" />
					<StatsRow :label="__('Recoveries')" :value="String(recoveryCount)" />
				</StatsSection>

				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<StatsSection :title="__('Sending')" :badge="String(sendStreams.length)">
					<StreamStats v-for="stream in sendStreams" :key="stream.id" :stream="stream" />
					<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
					<p v-if="!sendStreams.length" class="py-2 text-ink-gray-5">{{ __('No active outgoing streams') }}</p>
				</StatsSection>

				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<StatsSection :title="__('Receiving')" :badge="String(receiveStreams.length)">
					<StreamStats v-for="stream in receiveStreams" :key="stream.id" :stream="stream" />
					<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
					<p v-if="!receiveStreams.length" class="py-2 text-ink-gray-5">{{ __('No active incoming streams') }}</p>
				</StatsSection>

				<!-- //// Neoffice — i18n: text a person reads goes through __() (#1316) -->
				<StatsSection v-if="participantConnectionState.recoveryTimeline.length" :title="__('Recovery history')">
					<div v-for="entry in recentRecoveryTimeline" :key="`${entry.at}-${entry.state}`" class="border-b border-outline-gray-2 py-2 last:border-0">
						<div class="flex justify-between gap-3">
							<span class="capitalize text-ink-gray-7">{{ humanize(entry.state) }}</span>
							<time class="shrink-0 text-ink-gray-5">{{ formatTime(entry.at) }}</time>
						</div>
						<p v-if="entry.detail" class="mt-0.5 break-words text-ink-gray-5">{{ entry.detail }}</p>
					</div>
				</StatsSection>

				<p v-if="error" class="mt-3 rounded-4 bg-surface-red-2 px-2.5 py-2 text-ink-red-4">{{ error }}</p>
			</template>
		</div>
	</section>
</template>

<script setup lang="ts">
import { Tooltip } from "frappe-ui";
import { computed, defineComponent, h, ref } from "vue";
import LucideChevronDown from "~icons/lucide/chevron-down";
import LucideChevronUp from "~icons/lucide/chevron-up";
import LucideCopy from "~icons/lucide/copy";
import LucideX from "~icons/lucide/x";
import { useConnectionState } from "../composables/useConnectionState";
import { useParticipantConnectionState } from "../composables/useParticipantConnectionState";
import { useE2EEState } from "../composables/useE2EEState";
import { type RTCStreamStats, useRTCStats } from "../composables/useRTCStats";
import { setShowStatsForNerds } from "../data/statsPreferences";

const active = ref(true);
const expanded = ref(false);
const connectionState = useConnectionState();
const participantConnectionState = useParticipantConnectionState();
const e2eeState = useE2EEState();
const { snapshot, sendStreams, receiveStreams, error } = useRTCStats(active);

const qualityDot = computed(() => ({
	"bg-green-400": snapshot.value.quality === "good",
	"bg-amber-400": snapshot.value.quality === "poor",
	"bg-red-400": snapshot.value.quality === "critical",
	"bg-gray-500": snapshot.value.quality === "unknown",
}));

// //// Neoffice — i18n: upstream put the raw quality ("good", "poor", "critical", "unknown") into
// //// "{0} connection", so the header stayed English under any translation. One sentence per value
// //// reads naturally in every language; the old sentence stays for a value this list does not know (#1316).
const qualityLabel = computed(
	() =>
		({
			good: __("Good connection"),
			poor: __("Poor connection"),
			critical: __("Critical connection"),
			unknown: __("Unknown connection"),
		})[snapshot.value.quality] ?? __("{0} connection", [snapshot.value.quality]),
);

// //// Neoffice — i18n: text a person reads goes through __() (#1316)
const connectionStatus = computed(() => snapshot.value.signalingConnected ? __('Connected') : __('Disconnected'));
const transportStates = computed(() => ({
	send: humanize(snapshot.value.sendTransportState),
	receive: humanize(snapshot.value.receiveTransportState),
}));
const iceRoute = computed(() => {
	const local = snapshot.value.localCandidateType;
	const remote = snapshot.value.remoteCandidateType;
	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	return local || remote ? `${local || __('unknown')} → ${remote || __('unknown')}` : __('n/a');
});
const recoveryCount = computed(() => participantConnectionState.recoveryTimeline.filter((entry) => entry.state !== "healthy").length);
const recentRecoveryTimeline = computed(() => participantConnectionState.recoveryTimeline.slice(-8).reverse());
// //// Neoffice — i18n: text a person reads goes through __() (#1316)
const encryptionStatus = computed(() => e2eeState.isContextReady.value ? __('Active') : __('Not active'));

function close() {
	active.value = false;
	setShowStatsForNerds(false);
}

function formatBitrate(value?: number) {
	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	if (value === undefined || !Number.isFinite(value)) return __('n/a');
	if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)} Mbps`;
	if (value >= 1_000) return `${Math.round(value / 1_000)} kbps`;
	return `${Math.round(value)} bps`;
}

function formatMs(value?: number) {
	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	return value === undefined || !Number.isFinite(value) ? __('n/a') : `${Math.round(value)} ms`;
}

function formatPercent(value?: number) {
	// //// Neoffice — i18n: text a person reads goes through __() (#1316)
	return value === undefined || !Number.isFinite(value) ? __('n/a') : `${value.toFixed(1)}%`;
}

function humanize(value: string) {
	return value.replaceAll("_", " ");
}

function formatTime(value: string) {
	return new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

async function copyDiagnostics() {
	await navigator.clipboard.writeText(JSON.stringify({
		capturedAt: new Date().toISOString(),
		stats: snapshot.value,
		lifecycleState: participantConnectionState.lifecycleState,
		recoveryTimeline: participantConnectionState.recoveryTimeline,
	}, null, 2));
}

const StatValue = defineComponent({
	props: { label: { type: String, required: true }, value: { type: String, required: true } },
	setup: (props) => () => h("div", [
		h("p", { class: "text-ink-gray-5" }, props.label),
		h("p", { class: "mt-0.5 truncate font-mono text-[13px] text-ink-gray-8" }, props.value),
	]),
});

const StatsRow = defineComponent({
	props: { label: { type: String, required: true }, value: { type: String, required: true } },
	setup: (props) => () => h("div", { class: "flex justify-between gap-4 py-1" }, [
		h("span", { class: "text-ink-gray-5" }, props.label),
		h("span", { class: "break-all text-right font-mono text-ink-gray-7" }, props.value),
	]),
});

const StatsSection = defineComponent({
	props: { title: { type: String, required: true }, badge: String },
	setup: (props, { slots }) => () => h("section", { class: "mt-4 border-t border-outline-gray-2 pt-3" }, [
		h("div", { class: "mb-1 flex items-center gap-2" }, [
			h("h3", { class: "font-semibold text-ink-gray-7" }, props.title),
			props.badge ? h("span", { class: "rounded-4 bg-surface-gray-3 px-1.5 py-0.5 text-[10px] text-ink-gray-5" }, props.badge) : null,
		]),
		slots.default?.(),
	]),
});

const StreamStats = defineComponent({
	props: { stream: { type: Object as () => RTCStreamStats, required: true } },
	setup: (props) => () => {
		const stream = props.stream;
		// //// Neoffice — i18n: text a person reads goes through __() (#1316)
		const resolution = stream.width && stream.height ? `${Math.round(stream.width)}×${Math.round(stream.height)}` : __('n/a');
		const status = stream.paused ? __('paused') : stream.muted ? __('muted') : __('live');
		const rows = [
			// //// Neoffice — i18n: text a person reads goes through __() (#1316)
			[__('Status'), status],
			[__('Codec'), stream.codec || __('n/a')],
			[__('Resolution / FPS'), `${resolution} · ${stream.fps === undefined ? __('n/a') : Math.round(stream.fps)} fps`],
			[__('Bitrate'), formatBitrate(stream.bitrate)],
			[__('Packet loss / jitter'), `${formatPercent(stream.packetLoss)} · ${formatMs(stream.jitter)}`],
			[__('RTT'), formatMs(stream.rtt)],
			[__('Frames processed / dropped'), `${stream.framesProcessed ?? __('n/a')} / ${stream.framesDropped ?? __('n/a')}`],
			[__('Quality limitation'), stream.qualityLimitation || __('n/a')],
			[__('Scalability mode'), stream.scalabilityMode || __('n/a')],
			[__('NACK / PLI / FIR'), `${stream.nackCount ?? __('n/a')} / ${stream.pliCount ?? __('n/a')} / ${stream.firCount ?? __('n/a')}`],
			[__('Jitter buffer'), formatMs(stream.jitterBufferDelay)],
			[__('Audio concealed'), stream.concealedSamples === undefined ? __('n/a') : __('{0} / {1} samples', [stream.concealedSamples, stream.totalSamples ?? __('n/a')])],
		];
		return h("article", { class: "border-b border-outline-gray-2 py-2 last:border-0" }, [
			h("div", { class: "mb-1.5 flex items-center justify-between gap-3" }, [
				h("h4", { class: "capitalize text-ink-gray-7" }, stream.source),
				stream.participantId ? h("span", { class: "max-w-36 truncate font-mono text-[10px] text-ink-gray-5", title: stream.participantId }, stream.participantId) : null,
			]),
			...rows.map(([label, value]) => h(StatsRow, { label, value })),
		]);
	},
});
</script>
