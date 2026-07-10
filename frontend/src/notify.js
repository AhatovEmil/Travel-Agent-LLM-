/** Funny ready jingle + optional browser notification when a trip finishes. */

function tone(ctx, { type = 'square', freq, start, dur, peak = 0.07, slideTo }) {
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  const filter = ctx.createBiquadFilter()
  filter.type = 'lowpass'
  filter.frequency.value = 2800
  osc.type = type
  osc.frequency.setValueAtTime(freq, start)
  if (slideTo != null) {
    osc.frequency.exponentialRampToValueAtTime(Math.max(40, slideTo), start + dur)
  }
  gain.gain.setValueAtTime(0.0001, start)
  gain.gain.exponentialRampToValueAtTime(peak, start + 0.015)
  gain.gain.exponentialRampToValueAtTime(0.0001, start + dur)
  osc.connect(filter)
  filter.connect(gain)
  gain.connect(ctx.destination)
  osc.start(start)
  osc.stop(start + dur + 0.02)
}

/** Cartoon suitcase bounce → silly fanfare. */
export function playReadyChime() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext
    if (!Ctx) return
    const ctx = new Ctx()
    const t0 = ctx.currentTime

    // Boing-boing (suitcase hops)
    tone(ctx, { type: 'triangle', freq: 180, slideTo: 420, start: t0, dur: 0.14, peak: 0.09 })
    tone(ctx, { type: 'triangle', freq: 220, slideTo: 520, start: t0 + 0.12, dur: 0.13, peak: 0.08 })
    tone(ctx, { type: 'triangle', freq: 280, slideTo: 640, start: t0 + 0.24, dur: 0.12, peak: 0.07 })

    // Tiny "zip"
    tone(ctx, {
      type: 'sawtooth',
      freq: 900,
      slideTo: 1600,
      start: t0 + 0.38,
      dur: 0.09,
      peak: 0.035,
    })

    // Goofy victory: doo-doo-DOO!
    const fanfare = [
      { f: 392, at: 0.5, d: 0.11 },
      { f: 523.25, at: 0.6, d: 0.11 },
      { f: 659.25, at: 0.7, d: 0.22 },
      { f: 783.99, at: 0.82, d: 0.28 },
    ]
    fanfare.forEach(({ f, at, d }, i) => {
      tone(ctx, {
        type: i === fanfare.length - 1 ? 'triangle' : 'square',
        freq: f,
        start: t0 + at,
        dur: d,
        peak: i === fanfare.length - 1 ? 0.1 : 0.055,
      })
      // soft octave sparkle on the last hit
      if (i === fanfare.length - 1) {
        tone(ctx, {
          type: 'sine',
          freq: f * 2,
          start: t0 + at,
          dur: d * 0.7,
          peak: 0.03,
        })
      }
    })

    // Final comic "plink"
    tone(ctx, {
      type: 'sine',
      freq: 1318.5,
      slideTo: 1760,
      start: t0 + 1.12,
      dur: 0.16,
      peak: 0.06,
    })

    setTimeout(() => ctx.close().catch(() => {}), 1600)
  } catch {
    /* ignore */
  }
}

export async function ensureNotifyPermission() {
  if (!('Notification' in window)) return 'denied'
  if (Notification.permission === 'granted') return 'granted'
  if (Notification.permission === 'denied') return 'denied'
  try {
    return await Notification.requestPermission()
  } catch {
    return 'denied'
  }
}

export function showReadyNotification(tripName) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return
  try {
    const n = new Notification('Travel Agent', {
      body: `Готово: ${tripName} 🧳`,
      tag: 'travel-ready',
    })
    setTimeout(() => n.close(), 6000)
  } catch {
    /* ignore */
  }
}

export function announceTripReady(tripName, { toast } = {}) {
  playReadyChime()
  showReadyNotification(tripName)
  if (typeof toast === 'function') {
    toast(`План готов: ${tripName} 🧳`)
  }
}
