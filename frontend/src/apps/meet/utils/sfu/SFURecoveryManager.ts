/**
 * SFU Recovery Manager
 * Handles ICE restart and connection recovery logic
 */

import type { TransportManager } from "../media/TransportManager";
import type { SFUClient } from "../SFUClient";

interface RecoveryManagerOptions {
	sfuClient: SFUClient;
	transportManager: TransportManager;
	meetingId: () => string | null;
}

export class SFURecoveryManager {
	private sfuClient: SFUClient;
	private transportManager: TransportManager;
	private getMeetingId: () => string | null;
	private recoveryInProgress = false;
	private lastRecoveryAt = 0;
	private static readonly RECOVERY_COOLDOWN_MS = 7000;

	constructor(options: RecoveryManagerOptions) {
		this.sfuClient = options.sfuClient;
		this.transportManager = options.transportManager;
		this.getMeetingId = options.meetingId;
	}

	get isRecovering(): boolean {
		return this.recoveryInProgress;
	}

	async recoverTransportIce(reason: string): Promise<boolean> {
		if (this.recoveryInProgress) {
			return false;
		}

		if (!this.sfuClient?.isConnected?.()) {
			return false;
		}

		const now = Date.now();
		if (now - this.lastRecoveryAt < SFURecoveryManager.RECOVERY_COOLDOWN_MS) {
			return false;
		}

		this.recoveryInProgress = true;
		this.lastRecoveryAt = now;

		try {
			console.warn("Restarting SFU transport ICE", {
				reason,
				meetingId: this.getMeetingId(),
			});

			const restarted = await this.transportManager.restartAllTransportIce();
			if (!restarted) {
				return false;
			}

			console.log("SFU transport ICE restart completed", { reason });
			return true;
		} catch (error) {
			console.error("SFU transport ICE restart failed:", error);
			return false;
		} finally {
			this.recoveryInProgress = false;
		}
	}

	handleTransportConnectionStateChange(direction: string, state: string): void {
		if (state === "failed" || state === "closed") {
			this.recoverTransportIce(`transport_${direction}_${state}`);
		}
	}

	setupTransportEventHandlers(): void {
		this.transportManager.setEventHandlers({
			onTransportConnectionStateChange: ({
				direction,
				state,
			}: {
				direction: string;
				state: string;
			}) => {
				this.handleTransportConnectionStateChange(direction, state);
			},
		});
	}

	reset(): void {
		this.recoveryInProgress = false;
		this.lastRecoveryAt = 0;
	}
}
