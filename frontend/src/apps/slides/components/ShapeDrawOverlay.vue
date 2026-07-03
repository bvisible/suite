<template>
  <div v-if="pendingShapeType" :style="overlayStyles" @mousedown.prevent="handleMouseDown" />

  <div v-if="isDrawing" :style="previewStyles" />
</template>
<script setup>
import { computed, onMounted, onBeforeUnmount } from 'vue'

import { pendingShapeType, addShapeElement } from '@/apps/slides/stores/element'
import { slideBounds } from '@/apps/slides/stores/slide'
import { useDrawRect } from '@/apps/slides/composables/useDrawRect'

const { isDrawing, isShiftLocked, drawRect, startPoint, endPoint, startDrawing, cancelDrawing } =
  useDrawRect()

const overlayStyles = {
  position: 'absolute',
  inset: '0',
  cursor: 'crosshair',
  zIndex: 10000,
}

const MIN_SIZE = 10

const isLine = computed(() => pendingShapeType.value === 'line')

const snapToNearest45 = (p1, p2) => {
  const dx = p2.x - p1.x
  const dy = p2.y - p1.y

  const length = Math.hypot(dx, dy)
  const rawAngle = Math.atan2(dy, dx)
  const snappedAngle = Math.round(rawAngle / (Math.PI / 4)) * (Math.PI / 4)

  return {
    x: p1.x + length * Math.cos(snappedAngle),
    y: p1.y + length * Math.sin(snappedAngle),
  }
}

const activeEndPoint = computed(() =>
  isShiftLocked.value && isLine.value ? snapToNearest45(startPoint, endPoint) : endPoint
)

const previewBorderRadius = computed(() => {
  if (pendingShapeType.value === 'oval') return '50%'
  return '0'
})

const PREVIEW_CLIP_PATHS = {
  diamond: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
  triangle: 'polygon(50% 0%, 100% 100%, 0% 100%)',
  pentagon: 'polygon(50% 0%, 100% 38%, 81% 100%, 19% 100%, 0% 38%)',
}

const previewClipPath = computed(() => PREVIEW_CLIP_PATHS[pendingShapeType.value] ?? null)

const linePreviewStyles = computed(() => {
  const { x: x1, y: y1 } = startPoint
  const { x: x2, y: y2 } = activeEndPoint.value
  const dx = x2 - x1
  const dy = y2 - y1
  const length = Math.hypot(dx, dy)
  const angle = Math.atan2(dy, dx) * (180 / Math.PI)

  return {
    position: 'absolute',
    left: `${x1}px`,
    top: `${y1}px`,
    width: `${length}px`,
    height: `${Math.max(2 / slideBounds.scale, 2)}px`,
    transformOrigin: '0 50%',
    transform: `translate(0, -50%) rotate(${angle}deg)`,
    backgroundColor: '#70B6F092',
    zIndex: 10001,
    pointerEvents: 'none',
  }
})

const previewStyles = computed(() => {
  if (isLine.value) return linePreviewStyles.value

  const { left, top, width, height } = drawRect

  return {
    position: 'absolute',
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    backgroundColor: '#70b6f025',
    outline: `#70B6F092 solid ${0.1 / slideBounds.scale}px`,
    borderRadius: previewBorderRadius.value,
    clipPath: previewClipPath.value,
    boxSizing: 'border-box',
    zIndex: 10001,
    pointerEvents: 'none',
  }
})

const getLineBounds = (start, end) => ({
  x1: start.x,
  y1: start.y,
  x2: end.x,
  y2: end.y,
})

const isLineLongEnough = (start, end) => Math.hypot(end.x - start.x, end.y - start.y) >= MIN_SIZE

const isRectBigEnough = rect => rect.width >= MIN_SIZE && rect.height >= MIN_SIZE

const handleMouseDown = e => {
  startDrawing(e, (rect, start, end) => {
    if (isShiftLocked.value && isLine.value) end = snapToNearest45(start, end)

    const drawnAsLine = isLine.value
    const bounds = drawnAsLine ? getLineBounds(start, end) : rect
    const isBigEnough = drawnAsLine ? isLineLongEnough(start, end) : isRectBigEnough(rect)

    if (isBigEnough) addShapeElement(pendingShapeType.value, bounds)
    pendingShapeType.value = null
  })
}

const handleKeyDown = e => {
  if (e.key === 'Shift' && isDrawing.value) {
    isShiftLocked.value = true
  }
  if (e.key === 'Escape' && pendingShapeType.value) {
    cancelDrawing()
    pendingShapeType.value = null
  }
}

const handleKeyUp = e => {
  if (e.key === 'Shift') isShiftLocked.value = false
}

onMounted(() => {
  document.addEventListener('keydown', handleKeyDown)
  document.addEventListener('keyup', handleKeyUp)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('keyup', handleKeyUp)
  cancelDrawing()
})
</script>
