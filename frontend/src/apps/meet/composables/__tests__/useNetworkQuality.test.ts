import { afterEach, describe, expect, it, vi } from "vitest";
import { createApp, defineComponent, nextTick, ref, watchEffect } from "vue";
import { useNetworkQuality } from "../useNetworkQuality";

describe("useNetworkQuality", () => {
	afterEach(() => {
		vi.useRealTimers();
	});

	const mountWithStats = (stats: unknown, transportState = "connected") => {
		vi.useFakeTimers();

		const getNetworkStats = vi.fn().mockResolvedValue(stats);
		const sfuManager = ref({
			transportManager: {
				getTransportStats: () => ({
					sendTransport: { state: transportState },
					recvTransport: { state: transportState },
				}),
				getNetworkStats,
			},
		});

		const observed = ref("unknown");
		const root = document.createElement("div");

		const TestComponent = defineComponent({
			setup() {
				const { networkQuality } = useNetworkQuality();
				watchEffect(() => {
					observed.value = networkQuality.value;
				});
				return () => null;
			},
		});

		const app = createApp(TestComponent);
		app.provide("sfuManager", sfuManager);
		app.mount(root);

		return { observed, getNetworkStats, unmount: () => app.unmount() };
	};

	it("keeps quality good when RTT is moderately high but video bitrate is healthy", async () => {
		const { observed, unmount, getNetworkStats } = mountWithStats({
			rtt: 520,
			packetLoss: 1,
			availableOutgoingBitrate: 900_000,
			timestamp: Date.now(),
			isValid: true,
		});

		await vi.advanceTimersByTimeAsync(3000);
		await nextTick();

		expect(getNetworkStats).toHaveBeenCalledTimes(1);
		expect(observed.value).toBe("good");

		unmount();
	});

	it("marks quality poor when RTT is high and available bitrate drops to video degradation levels", async () => {
		const { observed, unmount } = mountWithStats({
			rtt: 520,
			packetLoss: 1,
			availableOutgoingBitrate: 250_000,
			timestamp: Date.now(),
			isValid: true,
		});

		await vi.advanceTimersByTimeAsync(3000);
		await nextTick();

		expect(observed.value).toBe("poor");

		unmount();
	});

	it("marks quality poor when packet loss alone is clearly high", async () => {
		const { observed, unmount } = mountWithStats({
			rtt: 150,
			packetLoss: 10,
			availableOutgoingBitrate: 900_000,
			timestamp: Date.now(),
			isValid: true,
		});

		await vi.advanceTimersByTimeAsync(3000);
		await nextTick();

		expect(observed.value).toBe("poor");

		unmount();
	});

	it("marks quality critical when RTT is severe and bitrate is critically low", async () => {
		const { observed, unmount } = mountWithStats({
			rtt: 950,
			packetLoss: 3,
			availableOutgoingBitrate: 150_000,
			timestamp: Date.now(),
			isValid: true,
		});

		await vi.advanceTimersByTimeAsync(3000);
		await nextTick();

		expect(observed.value).toBe("critical");

		unmount();
	});
});
