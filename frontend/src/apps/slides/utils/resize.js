const MIN_SIZE = {
  text: { width: 7, height: 7 },
  shape: { width: 10, height: 16 },
  image: { width: 20, height: 20 },
  video: { width: 20, height: 20 },
  default: { width: 10, height: 16 },
}

export const getMinSizeForElement = type => MIN_SIZE[type] ?? MIN_SIZE.default

export const isAspectLocked = type => type === 'image' || type === 'video'

// 2d vector helpers, all working on { x, y } points
const addVectors = (a, b) => ({ x: a.x + b.x, y: a.y + b.y })
const subtractVectors = (a, b) => ({ x: a.x - b.x, y: a.y - b.y })
const scaleVector = (v, factor) => ({ x: v.x * factor, y: v.y * factor })
const getLength = v => Math.hypot(v.x, v.y)
const getMidpoint = (a, b) => scaleVector(addVectors(a, b), 0.5)
const getAngle = v => (Math.atan2(v.y, v.x) * 180) / Math.PI

const getUnitVector = v => {
  const length = getLength(v)
  if (!length) return { x: 1, y: 0 }
  return scaleVector(v, 1 / length)
}

const getRotatedVector = (v, degrees) => {
  const radians = (degrees * Math.PI) / 180
  const cos = Math.cos(radians)
  const sin = Math.sin(radians)
  return { x: v.x * cos - v.y * sin, y: v.x * sin + v.y * cos }
}

const getCenter = box => ({ x: box.left + box.width / 2, y: box.top + box.height / 2 })

const getBoxFromCenter = (center, width, height) => ({
  width,
  height,
  left: center.x - width / 2,
  top: center.y - height / 2,
})

// the axis-aligned bounding box of `box` once it is rotated about its centre
export const getRotatedBoundingBox = (box, degrees) => {
  const radians = (degrees * Math.PI) / 180
  const cos = Math.abs(Math.cos(radians))
  const sin = Math.abs(Math.sin(radians))

  const width = box.width * cos + box.height * sin
  const height = box.width * sin + box.height * cos

  return getBoxFromCenter(getCenter(box), width, height)
}

// each handle keeps the opposite edge/corner fixed. these signs say where that
// fixed point sits relative to the centre, along the element's own axes.
// a 0 means that axis doesn't resize (a side handle).
const FIXED_SIGN = {
  right: { x: -1, y: 0 },
  left: { x: 1, y: 0 },
  bottom: { x: 0, y: -1 },
  top: { x: 0, y: 1 },
  'bottom-right': { x: -1, y: -1 },
  'bottom-left': { x: 1, y: -1 },
  'top-right': { x: -1, y: 1 },
  'top-left': { x: 1, y: 1 },
}

// new length of one side. the grabbed edge moves by `movementAlongAxis`; the
// opposite edge stays put. a fixedSign of 0 means this side doesn't resize.
const getResizedSide = (startLength, fixedSign, movementAlongAxis, minLength) => {
  if (!fixedSign) return startLength

  const resized = startLength - fixedSign * movementAlongAxis
  return Math.max(minLength, resized)
}

// how far the centre moves toward the grabbed edge, along the element's local axes
const getCenterShift = (fixedSign, startBox, width, height) => ({
  x: (-fixedSign.x * (width - startBox.width)) / 2,
  y: (-fixedSign.y * (height - startBox.height)) / 2,
})

export const getResizedBox = (start, handle, cursorMovement) => {
  const fixedSign = FIXED_SIGN[handle]
  if (!fixedSign) return null

  const minSize = getMinSizeForElement(start.type)
  // rotate the cursor onto the element's local axes
  const movementInLocalAxes = getRotatedVector(cursorMovement, -start.rotation)

  // resize as if unrotated, keeping the opposite edge fixed
  const width = getResizedSide(start.width, fixedSign.x, movementInLocalAxes.x, minSize.width)
  let height = getResizedSide(start.height, fixedSign.y, movementInLocalAxes.y, minSize.height)

  const isCornerHandle = fixedSign.x !== 0 && fixedSign.y !== 0
  if (isAspectLocked(start.type) && isCornerHandle) {
    height = width * (start.height / start.width)
  }

  // then move the centre so the fixed point stays put
  const centerShiftInLocalAxes = getCenterShift(fixedSign, start, width, height)
  const centerShiftInScreenAxes = getRotatedVector(centerShiftInLocalAxes, start.rotation)

  const newCenter = addVectors(getCenter(start), centerShiftInScreenAxes)

  return getBoxFromCenter(newCenter, width, height)
}

export const getResizedTextBox = (start, handle, cursorMovement) => {
  const minWidth = getMinSizeForElement(start.type).width
  const { left, top, height } = start

  // dragging the right edge: the left edge stays put, width grows with the cursor
  if (handle === 'text-right') {
    const width = Math.max(minWidth, start.width + cursorMovement.x)
    return { left, top, width, height }
  }

  // dragging the left edge: the right edge stays put, so the left edge moves in
  const width = Math.max(minWidth, start.width - cursorMovement.x)
  const rightEdge = left + start.width
  return { left: rightEdge - width, top, width, height }
}

const getLineEndpoints = box => {
  const center = getCenter(box)
  // line's own rotation determines which way is "along" the line
  const centerToRightEnd = getRotatedVector({ x: box.width / 2, y: 0 }, box.rotation)

  return {
    leftEnd: subtractVectors(center, centerToRightEnd),
    rightEnd: addVectors(center, centerToRightEnd),
  }
}

// the grabbed end can't come closer than minLength to the fixed end
const getClampedEnd = (fixedEnd, cursorTarget, minLength) => {
  const span = subtractVectors(cursorTarget, fixedEnd)
  if (getLength(span) >= minLength) return cursorTarget

  // too short: keep the drag direction but push the end out to the minimum
  const direction = getUnitVector(span)
  return addVectors(fixedEnd, scaleVector(direction, minLength))
}

export const getResizedLine = (start, handle, cursorMovement) => {
  const minLength = getMinSizeForElement(start.type).width

  // for line resize + rotate happens through endpoints
  const { leftEnd, rightEnd } = getLineEndpoints(start)

  const grabbingRightEnd = handle === 'line-right'
  const fixedEnd = grabbingRightEnd ? leftEnd : rightEnd
  const grabbedEnd = grabbingRightEnd ? rightEnd : leftEnd

  // add cursorMovement to the grabbed end and get new position of that endpoint
  const cursorTarget = addVectors(grabbedEnd, cursorMovement)
  const newEnd = getClampedEnd(fixedEnd, cursorTarget, minLength)

  // where the two ends sit now: the one we didn't grab stayed put
  const newLeftEnd = grabbingRightEnd ? fixedEnd : newEnd
  const newRightEnd = grabbingRightEnd ? newEnd : fixedEnd

  // the box spans between them: its length, centre, and angle
  const lineVector = subtractVectors(newRightEnd, newLeftEnd)
  const center = getMidpoint(newLeftEnd, newRightEnd)

  return {
    ...getBoxFromCenter(center, getLength(lineVector), start.height),
    rotation: getAngle(lineVector),
  }
}
