// Admin-only navigation adapter. No API requests, identity data or permissions.
const destination = "/admin-invitations/";
const nativeRoute = "#/flow/stages/invitations";
const roots = new WeakSet();
const pending = new WeakSet();

function repair(anchor) {
  const href = anchor.getAttribute("href") || "";
  if (!href.endsWith(nativeRoute)) return;
  if (anchor.parentElement?.querySelector('[data-cloud-invitation]')) return;
  const invite = anchor.cloneNode(true);
  invite.setAttribute("href", destination);
  invite.textContent = "Invite users";
  invite.setAttribute("aria-label", "Invite users");
  invite.dataset.cloudInvitation = "true";
  invite.addEventListener("click", (event) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    location.assign(destination);
  }, true);
  anchor.before(invite);
}

function scan(node) {
  if (node.nodeType === Node.ELEMENT_NODE) {
    if (node.matches("a[href]")) repair(node);
    if (node.shadowRoot) observe(node.shadowRoot);
    else if (node.localName.includes("-") && !pending.has(node)) {
      pending.add(node);
      customElements.whenDefined(node.localName).then(() => {
        if (node.isConnected && node.shadowRoot) observe(node.shadowRoot);
      });
    }
  }
  for (const child of node.children || []) scan(child);
}

function observe(root) {
  if (roots.has(root)) return;
  roots.add(root);
  new MutationObserver((records) => {
    for (const record of records) {
      if (record.type === "attributes") repair(record.target);
      for (const node of record.addedNodes) scan(node);
    }
  }).observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["href"] });
  scan(root);
}

if (location.pathname === "/if/admin/") observe(document);
