"""Guest page for outside responses (/o/<key>, /r/<key>, /v/<key>; route rules in hooks.py).

The HTML carries no data. After the person taps "Open", the page's script calls erpnext_drive_integrations.onboarding.respond.open_link,
which checks the key and locks the link to this device. Waiting for the tap keeps email link-scanners from
taking the lock.
"""
no_cache = 1


def get_context(context):
    context.no_cache = 1
    context.title = "Example Organization Constructions"
    # Outsiders get no staff scripts (header, session guard, push, test banner): they would only call
    # staff APIs that the public route blocks anyway. The page's own script is inline.
    context.web_include_js = []
    context.web_include_css = []
