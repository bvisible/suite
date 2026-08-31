import type { Platform } from "../types";
import { getPlatform } from "../utils/device";

/**
 * The suite's main.ts is shared and does not register meet globals, so
 * templates that reference `$platform` use this meet-local composable.
 */
export function usePlatform(): Platform {
	return getPlatform();
}
