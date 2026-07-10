// Build entry point for the desk bundle declared in hooks.py:
//     app_include_js = ["ff_integration.bundle.js"]
//
// Frappe's esbuild only discovers bundles under `apps/<app>/<app>/public/**`
// (esbuild/utils.js: public_paths[app] = apps/<app>/<app>/public). The real
// source lives one level deeper, in the drive module — suite/drive/public/js/ —
// next to the .vue files it imports, so esbuild never saw it and the bundle was
// never built. The desk then requested an asset that did not exist: on Osiris,
// assets.json still resolved it to the dead /assets/drive/dist/ path and the
// request 404'd.
//
// Re-exporting from here puts a discoverable entry point at the path esbuild
// scans, while the implementation stays with its Vue components.
import "../../drive/public/js/ff_integration.bundle.js";
