<template>
	<Dialog
		v-model="show"
		:options="{ size: '5xl' }"
	>
		<template #body>
			<div class="flex flex-col md:flex-row z-50" :style="{ height: 'calc(100vh - 8rem)' }">
				<div class="w-full" v-if="isMobile()">
					<h3
						class="text-2xl font-semibold leading-6 text-ink-gray-9 px-4 py-6">
						Settings
					</h3>
					<FTabs :tabs="flatTabs" v-model="tabIndex" as="div">
						<template #tab-item="{ tab, selected }">
							<div
								class="flex cursor-pointer items-center gap-1.5 py-3 text-base transition"
								:class="selected ? 'text-ink-gray-9' : 'text-ink-gray-5'"
							>
								<component v-if="tab.icon" :is="tab.icon" class="h-4 w-4" />
								{{ tab.label }}
							</div>
						</template>
						<template #tab-panel="{ tab }">
							<div class="flex flex-1 flex-col bg-surface-modal max-w-[816px] w-full">
								<component
									:is="tab.component"
									class="h-full flex flex-col w-full"
									@device-changed="$emit('device-changed', $event)"
									:is-visible="show"
									:meeting-id="meetingId"
								/>
							</div>
						</template>
					</FTabs>
				</div>
				<div class="w-full flex" v-else>
					<div
						class="flex w-52 shrink-0 flex-col bg-surface-gray-1 p-2 md:overflow-y-auto hide-scrollbar border-outline-gray-2 border-r"
					>
						<h1 class="px-2 pt-2 text-lg font-semibold mb-2">
							Settings
						</h1>
						<div v-for="tab in tabs">
							<div
								v-if="!tab.hideLabel"
								class="mb-2 ml-1 mt-3 hidden md:flex gap-1.5 px-1 text-base font-medium text-ink-gray-5"
							>
								<span>{{ tab.label }}</span>
							</div>
							<nav class="md:space-y-1">
								<button
									v-for="item in tab.items"
									:key="item.label"
									class="flex h-7 w-full items-center gap-2 rounded px-2 py-1"
									:class="[
										activeTab?.label == item.label
											? 'bg-surface-white shadow-sm'
											: 'hover:bg-surface-gray-2',
									]"
									@click="() => onTabChange(item)"
								>
									<component :is="item.icon" class="h-4 w-4 text-ink-gray-7" />
									<span class="text-base text-ink-gray-8">
										{{ item.label }}
									</span>
								</button>
							</nav>
						</div>
					</div>
					<div class="flex flex-1 flex-col bg-surface-modal max-w-[816px] w-full">
						<component
							:is="activeTab?.component"
							v-if="activeTab"
							class="h-full flex flex-col w-full"
							@device-changed="$emit('device-changed', $event)"
							:is-visible="show"
							:meeting-id="meetingId"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>


<script setup>
import { Dialog, Tabs as FTabs } from "frappe-ui";
import { computed, h, markRaw, ref, watch } from "vue";
import LucideAudioLines from "~icons/lucide/audio-lines";
import LucideBell from "~icons/lucide/bell";
import LucideCamera from "~icons/lucide/camera";
import LucideMonitorSmartphone from "~icons/lucide/monitor-smartphone";
import LucideUser from "~icons/lucide/user";
import { useMeetingDoc } from "../../composables/useMeetingDoc";
import { isMobile } from "../../utils/device";
import AudioSettingsTab from "./AudioSettingsTab.vue";
import BackgroundSettingsTab from "./BackgroundSettingsTab.vue";
import DeviceSettingsTab from "./DeviceSettingsTab.vue";
import MeetingAccessSettingsTab from "./MeetingAccessSettingsTab.vue";
import NotificationSettingsTab from "./NotificationSettingsTab.vue";

const props = defineProps({
	modelValue: {
		type: Boolean,
		default: false,
	},
	meetingId: {
		type: String,
		default: "",
	},
	isPreview: {
		type: Boolean,
		default: false,
	},
});

const emit = defineEmits(["device-changed", "update:modelValue"]);

const { isCurrentUserHost, isCurrentUserCohost, getMeetingDoc } =
	useMeetingDoc();

// sometimes we won't see meeting access tab right after creating a meeting
// this loads the meeting doc to avoid that
if (props.meetingId) {
	getMeetingDoc(props.meetingId);
}

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit("update:modelValue", value),
});

// Settings tabs structure
const tabs = computed(() => {
	const allTabs = [];

	if (
		(isCurrentUserHost.value || isCurrentUserCohost.value) &&
		!props.isPreview
	) {
		allTabs.push({
			label: "Meeting",
			items: [
				{
					label: "Meeting Access",
					value: "meeting-access",
					icon: h(LucideUser),
					component: markRaw(MeetingAccessSettingsTab),
				},
			],
		});
	}

	allTabs.push({
		label: "General",
		items: [
			{
				label: "Devices",
				value: "devices",
				icon: h(LucideMonitorSmartphone),
				component: markRaw(DeviceSettingsTab),
			},
			{
				label: "Audio",
				value: "audio",
				icon: h(LucideAudioLines),
				component: markRaw(AudioSettingsTab),
			},
			{
				label: "Background",
				value: "background",
				icon: h(LucideCamera),
				component: markRaw(BackgroundSettingsTab),
			},
			{
				label: "Notifications",
				value: "notifications",
				icon: h(LucideBell),
				component: markRaw(NotificationSettingsTab),
			},
		],
	});

	return allTabs;
});

const flatTabs = computed(() =>
	tabs.value.flatMap((group) =>
		group.items.map((item) => ({
			...item,
			groupLabel: group.label,
		})),
	),
);

const tabIndex = ref(0);
const activeTab = computed(() => flatTabs.value[tabIndex.value]);

watch(flatTabs, (newTabs) => {
	if (!newTabs.length) return;
	if (tabIndex.value >= newTabs.length) {
		tabIndex.value = 0;
	}
});

function onTabChange(tab) {
	const index = flatTabs.value.findIndex((item) => item.value === tab.value);
	if (index !== -1) {
		tabIndex.value = index;
	}
}
</script>
