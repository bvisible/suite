import type { Platform } from "../types";
import { getPlatform } from "../utils/device";

/**
 * The standalone app exposed `getPlatform()` globally as `$platform` via
 * `app.config.globalProperties`. The suite's main.ts is shared and does not
 * register meet globals, so templates that referenced `$platform` use this
 * meet-local composable instead.
 */
export function usePlatform(): Platform {
	return getPlatform();
}
