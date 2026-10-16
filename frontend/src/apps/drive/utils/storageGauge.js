//// Neoffice — added file (no upstream equivalent): what the Drive's storage bar shows (maintenance#1598).
//// With a quota: the person's use of it. Without one: the volume the Drive writes its files to, its size and what is
//// used of it (suite/drive/api/storage.py, drive_disk), where the bar said « / 5 GB », a limit no server has
//// (Jérémy, 16.10.2026). Files kept on S3, with no volume to say: the person's use alone, and no bar.
export function storageGauge(data) {
  const quota = Number(data?.limit) || 0
  if (quota > 0) {
    const used = Number(data.total_size) || 0
    return { used, limit: quota, percent: Math.min(100, (100 * used) / quota), volume: false }
  }
  const total = Number(data?.disk?.total) || 0
  if (total > 0) {
    const used = Number(data.disk.used) || 0
    return { used, limit: total, percent: Math.min(100, (100 * used) / total), volume: true }
  }
  return { used: Number(data?.total_size) || 0, limit: 0, percent: 0, volume: false }
}
