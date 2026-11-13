<template>
	<Tooltip v-if="severity" :text="message" class="contents">
		<div
			v-bind="$attrs"
			class="bg-gray-700 rounded-full p-1.5 ring-1 ring-gray-800"
			role="img"
			:aria-label="message"
			:data-network-status="severity"
		>
			<WifiAlertIcon class="w-4 h-4 text-white" />
		</div>
	</Tooltip>
</template>

<script setup lang="ts">
import { Tooltip } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref } from "vue";
import WifiAlertIcon from "../icons/WifiAlertIcon.vue";
import type { MediaHealthState } from "../utils/media/MediaHealthMonitor";

defineOptions({ inheritAttrs: false });
const props = withDefaults(
	defineProps<{
		health?: MediaHealthState;
		quality?: string;
		updatedAt?: number;
		participantName?: string;
		isLocal?: boolean;
	}>(),
	{ participantName: "This participant", isLocal: false },
);
const now = ref(Date.now());
let timer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
	if (!props.health)
		timer = setInterval(() => {
			now.value = Date.now();
		}, 3000);
});
onUnmounted(() => clearInterval(timer));
const severity = computed(() => {
	if (props.health) {
		const { networkQuality, downlinkQuality, isTransportFailed, status } =
			props.health;
		if (
			isTransportFailed ||
			status === "disconnected" ||
			networkQuality === "critical" ||
			downlinkQuality === "critical"
		)
			return "critical";
		if (networkQuality === "poor" || downlinkQuality === "poor") return "poor";
		return null;
	}
	if (
		!props.isLocal &&
		(!props.updatedAt || now.value - props.updatedAt > 15_000)
	)
		return null;
	return props.quality === "poor" || props.quality === "critical"
		? props.quality
		: null;
});
const message = computed(() => {
	const local = props.isLocal || !!props.health;
	// //// Neoffice — i18n: text a person reads goes through __() (#1316). Upstream moved these four sentences here
	// //// from ParticipantTile.vue, where we had them translated; the build's plugin does not read a bare return.
	if (severity.value === "critical")
		return local
			? __("Your internet connection is unstable. Video and audio might lag or drop.")
			: __("{0}'s internet connection is unstable.", [props.participantName]);
	// //// Neoffice — the same (#1316)
	return local
		? __("Your internet connection is weak. You might notice some lag.")
		: __("{0}'s internet connection is weak.", [props.participantName]);
});
</script>
