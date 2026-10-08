//// Neoffice — added file (no upstream equivalent). The suite's code calls the global `__()`, installed at boot by
//// @/boot/translation; a test runs no boot, so a composable that translates a message threw `__ is not defined`
//// (#1316). A component mounted on a bare createApp still needs `app.use(translationPlugin)` for its template.
import { translate } from "@/boot/translation";

Object.assign(globalThis, { __: translate });
