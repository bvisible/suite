<template>
	<div class="min-h-screen bg-gray-50">
		<!-- Header -->
		<div class="bg-white shadow">
			<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
				<div class="flex justify-between items-center py-6">
					<div class="flex items-center">
						<router-link to="/" class="text-blue-600 hover:text-blue-500 mr-4">
							← Back to Home
						</router-link>
						<h1 class="text-3xl font-bold text-gray-900">SFU Dashboard</h1>
					</div>
					<div class="flex items-center space-x-4">
						<div class="text-sm text-gray-500">Last updated: {{ lastUpdated }}</div>
						<Button @click="refreshAll" :loading="refreshing" variant="outline">
							Refresh All
						</Button>
					</div>
				</div>
			</div>
		</div>

		<!-- Main Content -->
		<div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
			<!-- Page Description -->
			<div class="mb-6">
				<p class="text-lg text-gray-600">
					Monitor and manage your SFU (Selective Forwarding Unit) server for video
					conferencing.
				</p>
			</div>

			<!-- SFU Dashboard Component -->
			<SFUDashboard />

			<!-- Additional Admin Sections -->
			<div class="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Server Logs -->
				<Card title="Recent Server Logs" class="w-full">
					<div class="space-y-2 max-h-64 overflow-y-auto">
						<div v-if="serverLogs.length === 0" class="text-gray-500 text-center py-4">
							No recent logs available
						</div>
						<div
							v-for="(log, index) in serverLogs"
							:key="index"
							class="text-xs font-mono p-2 rounded"
							:class="{
								'bg-red-50 text-red-700': log.level === 'error',
								'bg-yellow-50 text-yellow-700': log.level === 'warning',
								'bg-blue-50 text-blue-700': log.level === 'info',
								'bg-gray-50 text-gray-700': log.level === 'debug',
							}"
						>
							<div class="flex justify-between items-start">
								<span>[{{ log.timestamp }}]</span>
								<span class="uppercase text-xs font-bold">{{ log.level }}</span>
							</div>
							<div class="mt-1">{{ log.message }}</div>
						</div>
					</div>
					<div class="mt-4 flex justify-between">
						<Button @click="clearLogs" variant="outline" size="sm">
							Clear Logs
						</Button>
						<Button @click="downloadLogs" variant="outline" size="sm">
							Download Logs
						</Button>
					</div>
				</Card>

				<!-- System Resources -->
				<Card title="System Resources" class="w-full">
					<div class="space-y-4">
						<!-- CPU Usage -->
						<div>
							<div class="flex justify-between text-sm">
								<span>CPU Usage</span>
								<span>{{ systemStats.cpu_usage }}%</span>
							</div>
							<div class="mt-1 w-full bg-gray-200 rounded-full h-2">
								<div
									class="h-2 rounded-full transition-all duration-300"
									:class="{
										'bg-green-500': systemStats.cpu_usage < 50,
										'bg-yellow-500':
											systemStats.cpu_usage >= 50 &&
											systemStats.cpu_usage < 80,
										'bg-red-500': systemStats.cpu_usage >= 80,
									}"
									:style="{ width: systemStats.cpu_usage + '%' }"
								></div>
							</div>
						</div>

						<!-- Memory Usage -->
						<div>
							<div class="flex justify-between text-sm">
								<span>Memory Usage</span>
								<span>{{ systemStats.memory_usage }}%</span>
							</div>
							<div class="mt-1 w-full bg-gray-200 rounded-full h-2">
								<div
									class="h-2 rounded-full transition-all duration-300"
									:class="{
										'bg-green-500': systemStats.memory_usage < 50,
										'bg-yellow-500':
											systemStats.memory_usage >= 50 &&
											systemStats.memory_usage < 80,
										'bg-red-500': systemStats.memory_usage >= 80,
									}"
									:style="{ width: systemStats.memory_usage + '%' }"
								></div>
							</div>
						</div>

						<!-- Network -->
						<div class="grid grid-cols-2 gap-4 text-sm">
							<div>
								<span class="text-gray-600">Upload</span>
								<div class="font-mono">
									{{ formatBytes(systemStats.network_up) }}/s
								</div>
							</div>
							<div>
								<span class="text-gray-600">Download</span>
								<div class="font-mono">
									{{ formatBytes(systemStats.network_down) }}/s
								</div>
							</div>
						</div>

						<!-- Uptime -->
						<div class="text-sm">
							<span class="text-gray-600">Uptime:</span>
							<span class="font-mono ml-2">{{
								formatUptime(systemStats.uptime)
							}}</span>
						</div>
					</div>
				</Card>
			</div>

			<!-- Configuration Panel -->
			<Card title="SFU Configuration" class="w-full mt-6">
				<div class="space-y-4">
					<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								SFU Server URL
							</label>
							<input
								v-model="configForm.server_url"
								type="text"
								class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
								placeholder="http://localhost:3000"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 mb-1">
								SFU Server Port
							</label>
							<input
								v-model="configForm.server_port"
								type="number"
								class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
								placeholder="3000"
							/>
						</div>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 mb-1">
							Maximum Participants per Room
						</label>
						<input
							v-model="configForm.max_participants"
							type="number"
							class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500"
							placeholder="50"
						/>
					</div>

					<div class="flex space-x-4">
						<Button @click="saveConfiguration" :loading="savingConfig">
							Save Configuration
						</Button>
						<Button @click="resetConfiguration" variant="outline">
							Reset to Defaults
						</Button>
					</div>
				</div>
			</Card>
		</div>
	</div>
</template>

<script>
import SFUDashboard from "@/components/SFUDashboard.vue";
import { Button, Card } from "frappe-ui";

export default {
	name: "SFUDashboardPage",
	components: {
		SFUDashboard,
		Card,
		Button,
	},
	data() {
		return {
			lastUpdated: new Date().toLocaleTimeString(),
			refreshing: false,
			savingConfig: false,
			serverLogs: [
				{
					timestamp: "2025-07-17 14:30:15",
					level: "info",
					message: "SFU server started successfully on port 3000",
				},
				{
					timestamp: "2025-07-17 14:30:20",
					level: "info",
					message: "MediaSoup workers initialized: 4 workers",
				},
				{
					timestamp: "2025-07-17 14:32:45",
					level: "info",
					message: "New room created: meeting-123",
				},
				{
					timestamp: "2025-07-17 14:33:10",
					level: "warning",
					message: "High CPU usage detected: 85%",
				},
				{
					timestamp: "2025-07-17 14:35:00",
					level: "error",
					message: "Failed to create WebRTC transport for peer-456",
				},
			],
			systemStats: {
				cpu_usage: 45,
				memory_usage: 62,
				network_up: 1024000, // bytes
				network_down: 2048000, // bytes
				uptime: 86400, // seconds
			},
			configForm: {
				server_url: "http://localhost:3000",
				server_port: 3000,
				max_participants: 50,
			},
		};
	},
	mounted() {
		this.startAutoRefresh();
		this.loadConfiguration();
	},
	beforeUnmount() {
		if (this.refreshInterval) {
			clearInterval(this.refreshInterval);
		}
	},
	methods: {
		async refreshAll() {
			this.refreshing = true;
			try {
				// Simulate API calls
				await new Promise((resolve) => setTimeout(resolve, 1000));
				this.lastUpdated = new Date().toLocaleTimeString();
				this.updateSystemStats();
			} finally {
				this.refreshing = false;
			}
		},

		updateSystemStats() {
			// Simulate real-time stats update
			this.systemStats.cpu_usage = Math.floor(Math.random() * 100);
			this.systemStats.memory_usage = Math.floor(Math.random() * 100);
			this.systemStats.network_up = Math.floor(Math.random() * 5000000);
			this.systemStats.network_down = Math.floor(Math.random() * 10000000);
		},

		startAutoRefresh() {
			this.refreshInterval = setInterval(() => {
				this.updateSystemStats();
				this.lastUpdated = new Date().toLocaleTimeString();
			}, 5000); // Update every 5 seconds
		},

		clearLogs() {
			this.serverLogs = [];
			this.$toast.success("Logs cleared successfully");
		},

		downloadLogs() {
			const logData = this.serverLogs
				.map(
					(log) =>
						`[${log.timestamp}] ${log.level.toUpperCase()}: ${log.message}`,
				)
				.join("\n");

			const blob = new Blob([logData], { type: "text/plain" });
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = `sfu-logs-${new Date().toISOString().split("T")[0]}.txt`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			window.URL.revokeObjectURL(url);
		},

		async saveConfiguration() {
			this.savingConfig = true;
			try {
				// Simulate API call
				await new Promise((resolve) => setTimeout(resolve, 1000));
				this.$toast.success("Configuration saved successfully");
			} catch (error) {
				this.$toast.error("Failed to save configuration");
			} finally {
				this.savingConfig = false;
			}
		},

		resetConfiguration() {
			this.configForm = {
				server_url: "http://localhost:3000",
				server_port: 3000,
				max_participants: 50,
			};
			this.$toast.success("Configuration reset to defaults");
		},

		loadConfiguration() {
			// Load configuration from API or local storage
			// For now, using default values
		},

		formatBytes(bytes) {
			if (bytes === 0) return "0 B";
			const k = 1024;
			const sizes = ["B", "KB", "MB", "GB"];
			const i = Math.floor(Math.log(bytes) / Math.log(k));
			return `${Number.parseFloat((bytes / k ** i).toFixed(2))} ${sizes[i]}`;
		},

		formatUptime(seconds) {
			const days = Math.floor(seconds / 86400);
			const hours = Math.floor((seconds % 86400) / 3600);
			const minutes = Math.floor((seconds % 3600) / 60);

			if (days > 0) {
				return `${days}d ${hours}h ${minutes}m`;
			}
			if (hours > 0) {
				return `${hours}h ${minutes}m`;
			}
			return `${minutes}m`;
		},
	},
};
</script>

<style scoped>
/* Add any custom styles here */
</style>
