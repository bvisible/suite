export type Platform = "win" | "mac" | "linux" | "unknown";

export interface FrappeRequestError extends Error {
	messages: string[];
}
