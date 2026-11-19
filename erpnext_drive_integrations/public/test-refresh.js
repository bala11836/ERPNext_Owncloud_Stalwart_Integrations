/* Test-only status panel. Production never renders or loads this module. */
(() => {
  'use strict';
  const panel = document.getElementById('ph-test-refresh');
  if (!panel) return;
  const button = panel.querySelector('button');
  const progress = panel.querySelector('[data-progress]');
  const last = panel.querySelector('[data-last-refresh]');
  const base = '/api/method/erpnext_drive_integrations.portal.test_refresh.';
  const csrf = document.querySelector('meta[name="test-refresh-csrf"]')?.content;
  let polling;
  let observedRefresh = false;
  const running = new Set(['queued', 'snapshotting', 'transferring', 'restoring', 'validating']);
  async function confirmRefresh() {
    let dialog = panel.querySelector('dialog');
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.className = 'ph-refresh-confirm';
      dialog.setAttribute('aria-labelledby', 'ph-refresh-confirm-title');
      dialog.innerHTML = '<form method="dialog"><h3 id="ph-refresh-confirm-title">Replace test data?</h3>'
        + '<p>Replace data in test ERP, Drive, DMS and Mail with a fresh production snapshot? Test changes will be replaced. '
        + 'Production apps pause briefly while a consistent snapshot is prepared. Nothing is copied back to production.</p>'
        + '<div><button value="cancel" autofocus>Cancel</button><button value="confirm">Refresh all four apps</button></div></form>';
      panel.append(dialog);
    }
    dialog.returnValue = 'cancel';
    return new Promise(resolve => {
      dialog.addEventListener('close', () => resolve(dialog.returnValue === 'confirm'), {once: true});
      dialog.showModal();
    });
  }
  async function update() {
    try {
      const response = await fetch(base + 'status', {credentials: 'same-origin', cache: 'no-store'});
      if (!response.ok) throw new Error('Temporarily unavailable');
      const {message: state} = await response.json();
      last.textContent = state.last_successful_at
        ? new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'long'}).format(new Date(state.last_successful_at))
        : 'Not refreshed yet';
      progress.textContent = ({idle: 'Test data is independent of production.',
        queued: 'Refresh queued…', snapshotting: 'Preparing production snapshot…',
        transferring: 'Copying snapshot to test…', restoring: 'Replacing test data…',
        validating: 'Checking restored data…', succeeded: 'Refresh completed.',
        failed: 'Refresh failed. The last successful refresh time is unchanged.'})[state.phase] || 'Checking refresh…';
      if (button) button.disabled = running.has(state.phase);
      clearTimeout(polling);
      if (running.has(state.phase)) {
        observedRefresh = true;
        panel.dataset.refreshActive = 'true';
        polling = setTimeout(update, 5000);
      } else if (observedRefresh) {
        // Native sessions are intentionally quarantined by restoration. A
        // normal home navigation obtains a new session through existing SSO
        // and discards any stale cached app frames/CSRF state.
        polling = setTimeout(() => location.replace('/'), 1500);
      } else {
        delete panel.dataset.refreshActive;
      }
    } catch (_) {
      progress.textContent = 'Test is temporarily unavailable. Reconnecting…';
      clearTimeout(polling);
      polling = setTimeout(update, 5000);
    }
  }
  button?.addEventListener('click', async () => {
    if (!await confirmRefresh()) return;
    panel.dataset.refreshActive = 'true';
    observedRefresh = true;
    button.disabled = true;
    try {
      const response = await fetch(base + 'request_refresh', {method: 'POST', credentials: 'same-origin',
        headers: {'X-Frappe-CSRF-Token': csrf, 'Content-Type': 'application/json'}, body: '{}'});
      if (!response.ok) throw new Error('Refresh request rejected');
      progress.textContent = 'Refresh queued…';
      polling = setTimeout(update, 2000);
    } catch (_) {
      delete panel.dataset.refreshActive;
      observedRefresh = false;
      progress.textContent = 'Could not request refresh. Sign in again or ask a test administrator.';
      button.disabled = false;
    }
  });
  update();
})();
