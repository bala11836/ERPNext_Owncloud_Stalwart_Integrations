import { InvitationClient, InvitationError } from "./invitations.mjs";

import { mailAvailable, test } from "./invite-mode.mjs";

const client = new InvitationClient({ test });
let delivery;
const $ = (id) => document.getElementById(id);
let options = new Map();
let pending = false;

function status(message, error = false) {
  $("status").textContent = message;
  $("status").className = error ? "error" : "";
}

function previewExpiry() {
  const expires = new Date(Date.now() + Number($("expiry").value) * 3600000);
  $("expires-at").textContent = `Expires ${expires.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} (${Intl.DateTimeFormat().resolvedOptions().timeZone}).`;
}

function previewUser() {
  $("user").setCustomValidity("");
  const selected = options.get($("user").value);
  $("invitation-kind").textContent = selected
    ? selected.invitationKind === "recovery"
      ? "Passkey recovery — old passkeys will be deleted after the replacement is registered."
      : "First-time enrollment — the user will register their first passkey."
    : "";
  if (test) {
    if (!mailAvailable) {
      $("delivery").textContent = "Test invitation email is unavailable. No invitation will be created.";
      return;
    }
    $("delivery").textContent = delivery
      ? `The test invitation will be sent to your administrator mailbox, ${delivery}.`
      : "Set an email address on your administrator account to receive test invitations.";
    return;
  }
  $("delivery").textContent = selected
    ? `Send to ${selected.email} from noreply@example.com.`
    : "The invitation will be sent from noreply@example.com.";
}

async function load() {
  if (pending) return;
  $("invite-form").hidden = true;
  $("sign-in").hidden = true;
  $("reload").hidden = true;
  options = new Map();
  $("users").replaceChildren();
  $("user").value = "";
  previewUser();
  status("Loading eligible users…");
  try {
    const result = await client.load();
    const { users } = result;
    delivery = result.delivery;
    if (test) {
      $("intro").textContent = "Send a first-time passkey invitation for a synthetic test account.";
      $("eligibility").textContent = "Only synthetic accounts awaiting their first passkey appear here.";
      $("footnote").textContent = "Test invitations are single-use. Register a separate passkey on the test host.";
    }
    for (const user of users) {
      const label = `${user.name || user.username} — ${user.username} — ${user.email}`;
      const option = document.createElement("option");
      option.value = label;
      $("users").append(option);
      options.set(label, user);
    }
    previewUser();
    $("invite-form").hidden = users.length === 0;
    $("reload").hidden = false;
    $("send").disabled = !mailAvailable;
    status(users.length ? "Choose a user and an expiry." : "No eligible users found. Create or approve the user in Authentik, then refresh this list.");
    previewExpiry();
  } catch (error) {
    status(error instanceof InvitationError ? error.message : "The page could not load. Refresh to try again.", true);
    $("sign-in").hidden = false;
    $("reload").hidden = false;
  }
}

$("expiry").addEventListener("change", previewExpiry);
$("user").addEventListener("input", previewUser);
$("reload").addEventListener("click", load);
$("invite-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (pending || !mailAvailable) return;
  const user = options.get($("user").value);
  if (!user) {
    $("user").setCustomValidity("Select an approved user from the list.");
    $("user").reportValidity();
    return;
  }
  pending = true;
  for (const id of ["send", "reload", "user", "expiry"]) $(id).disabled = true;
  $("send").textContent = "Sending…";
  status("Checking eligibility and sending the invitation…");
  try {
    const result = await client.send(user.pk, Number($("expiry").value));
    status(`${result.kind === "recovery" ? "Recovery" : "Enrollment"} invitation queued for ${result.email}. It expires ${new Date(result.expires).toLocaleString()}. Check Authentik System Tasks if the email does not arrive.`);
    $("invite-form").hidden = true;
  } catch (error) {
    status(error instanceof InvitationError ? error.message : "The invitation could not be completed. Check Authentik Invitations before retrying.", true);
  } finally {
    pending = false;
    for (const id of ["send", "reload", "user", "expiry"]) $(id).disabled = false;
    $("send").textContent = "Send invitation";
  }
});

// No storage, service worker, external scripts, analytics or embedded credentials.
load();
