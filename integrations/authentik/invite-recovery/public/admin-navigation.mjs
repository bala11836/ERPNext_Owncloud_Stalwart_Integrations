// Keep native invitation management and offer the user-selection companion.
const destination = "/admin-invitations/";
const nativeRoute = "#/flow/stages/invitations";
const roots = new WeakSet();
const pending = new WeakSet();
function addCompanion(anchor) {
  const href = anchor.getAttribute("href") || "";
  if (!href.endsWith(nativeRoute)) return;
  const root = anchor.getRootNode();
  if (root.host?.localName !== "ak-sidebar-item") return;
  const nativeItem = anchor.closest("li");
  if (!nativeItem || root.querySelector("[data-invite-companion]")) return;
  const item = document.createElement("li");
  item.className = nativeItem.className;
  item.setAttribute("role", "presentation");
  item.dataset.inviteCompanion = "true";
  const link = document.createElement("a");
  link.href = destination;
  link.textContent = "Invite users";
  link.className = "pf-c-nav__link";
  link.setAttribute("aria-label", "Invite users");
  link.addEventListener("click", event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    location.assign(destination);
  }, true);
  item.append(link);
  nativeItem.before(item);
}
function scan(node) {
  if (node.nodeType === Node.ELEMENT_NODE) {
    if (node.matches("a[href]")) addCompanion(node);
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
  new MutationObserver(records => {
    for (const record of records) {
      if (record.type === "attributes") addCompanion(record.target);
      for (const node of record.addedNodes) scan(node);
    }
  }).observe(root, {childList: true, subtree: true, attributes: true, attributeFilter: ["href"]});
  scan(root);
}
if (location.pathname === "/if/admin/") observe(document);
