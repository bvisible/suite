<template>
  <!-- Mobile / narrow-tablet blocker. The canvas grid has no touch support
       today, so we hide the editor behind this overlay below 720px. The
       underlying editor still mounts so state is preserved on rotate-back. -->
  <div class="sn-mobile-blocker">
    <div class="sn-mobile-card">
      <svg width="56" height="56" viewBox="0 0 256 256" fill="none">
        <rect width="256" height="256" rx="60" fill="#0E7490" />
        <g stroke="white" stroke-opacity="0.18" stroke-width="2" stroke-linecap="round">
          <line x1="85" y1="32" x2="85" y2="224" />
          <line x1="171" y1="32" x2="171" y2="224" />
          <line x1="32" y1="85" x2="224" y2="85" />
          <line x1="32" y1="171" x2="224" y2="171" />
        </g>
        <polyline
          points="48,180 96,148 136,164 184,80 216,108"
          fill="none"
          stroke="#A5F0FA"
          stroke-width="18"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        <circle cx="136" cy="164" r="11" fill="white" />
        <circle cx="184" cy="80" r="11" fill="white" />
      </svg>
      <h2>Open on desktop</h2>
      <p>
        Frappe Sheets is built for desktop browsers — mobile and tablet support
        is on the roadmap. Please come back from a laptop or PC.
      </p>
    </div>
  </div>

  <SheetEditor :id="id" @close="goHome" @saved="onSaved" />
  <Dialogs />
</template>

<script setup>
import { Dialogs } from 'frappe-ui'
import { useRouter } from 'vue-router'

import SheetEditor from '@/apps/sheets/components/SheetEditor/index.vue'

defineProps({
  // The sheet name (route param). 'new' is the special create id, preserved
  // from the standalone app's `?id=new`.
  id: { type: String, default: 'new' },
})

const router = useRouter()

function goHome() {
  router.push({ name: 'sheets-home' })
}

// After a brand-new sheet is persisted the editor emits the server-assigned
// name; swap the URL (replace, not push) from /sheets/new to /sheets/<name>
// so a reload / share-link points at the real doc — mirrors the old
// history.replaceState(`?id=${name}`).
function onSaved(name) {
  if (!name) return
  router.replace({ name: 'sheets-editor', params: { id: name } })
}
</script>

<style scoped>
.sn-mobile-blocker {
  display: none;
}
@media (max-width: 720px) {
  .sn-mobile-blocker {
    display: flex;
    position: fixed;
    inset: 0;
    z-index: 99999;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: var(--surface-gray-1, #f8f8f8);
    font-family: InterVar, ui-sans-serif, system-ui, sans-serif;
    color: var(--ink-gray-9, #171717);
  }
  .sn-mobile-card {
    max-width: 360px;
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 32px 24px;
    border-radius: 14px;
    background: var(--surface-base, #ffffff);
    border: 1px solid var(--outline-gray-2, #e2e2e2);
    box-shadow:
      0 0 1px rgba(0, 0, 0, 0.35),
      0 6px 8px -4px rgba(0, 0, 0, 0.1);
  }
  .sn-mobile-card h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.005em;
  }
  .sn-mobile-card p {
    margin: 0;
    font-size: 14px;
    line-height: 1.5;
    letter-spacing: 0.02em;
    color: var(--ink-gray-7, #525252);
  }
}
</style>
