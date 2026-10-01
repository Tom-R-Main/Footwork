/** Recover a recorder's polling only after rechecking its declared origin. */
export function createPollingSupervisor({ capture, tab, allowedOrigin, intervalMs = 500, retryMs = 750 } = {}) {
  let origin;
  try { origin = new URL(allowedOrigin); } catch { /* Validation below. */ }
  if (!origin || origin.protocol !== 'https:' || origin.origin !== allowedOrigin ||
      !capture?.status || !capture?.startPolling || !tab?.url) throw new Error('Recorder, tab and exact HTTPS origin required');
  if (!Number.isInteger(intervalMs) || intervalMs < 100 || intervalMs > 10000 ||
      !Number.isInteger(retryMs) || retryMs < 100 || retryMs > 10000) throw new Error('Invalid polling interval');
  let active = false, timer, inFlight;
  const metrics = { checks: 0, originUnavailable: 0, foreignOrigin: 0, statusFailures: 0, resumeAttempts: 0, resumed: 0, resumeFailures: 0 };
  const status = () => ({ active, ...metrics });
  const schedule = () => {
    if (!active) return;
    timer = setTimeout(async () => {
      timer = undefined;
      try { await recoverOnce(); } catch { metrics.statusFailures++; } finally { schedule(); }
    }, retryMs);
  };
  const recoverOnce = () => {
    if (inFlight) return inFlight;
    inFlight = (async () => {
      if (!active) return status();
      let state;
      try { state = capture.status(); } catch { metrics.statusFailures++; return status(); }
      if (!state.started || state.stopping || state.stopped || state.originPaused || state.polling?.active ||
          !state.polling?.everStarted || state.polling?.pauseReason !== 'origin-check-unavailable') return status();
      metrics.checks++;
      let current;
      try { current = new URL(await tab.url()); } catch { metrics.originUnavailable++; return status(); }
      if (!active) return status();
      if (current.origin !== allowedOrigin) { metrics.foreignOrigin++; return status(); }
      let latest;
      try { latest = capture.status(); } catch { metrics.statusFailures++; return status(); }
      if (!latest.started || latest.stopping || latest.stopped || latest.originPaused || latest.polling?.active ||
          !latest.polling?.everStarted || latest.polling?.pauseReason !== 'origin-check-unavailable') return status();
      metrics.resumeAttempts++;
      try { await capture.startPolling({ intervalMs }); metrics.resumed++; }
      catch { metrics.resumeFailures++; }
      return status();
    })().finally(() => { inFlight = undefined; });
    return inFlight;
  };
  return {
    async start() {
      if (active) throw new Error('Supervisor already started');
      active = true;
      try { await recoverOnce(); } finally { schedule(); }
      return status();
    },
    recoverOnce,
    status,
    async stop() {
      active = false;
      if (timer !== undefined) clearTimeout(timer);
      timer = undefined;
      if (inFlight) await inFlight;
      return status();
    },
  };
}
