#!/usr/bin/env python3
"""Use the pinned Insights session API to establish frontend identity."""

from pathlib import Path
import re
import sys


def patch(root):
    file = Path(root) / "frontend/src2/session.ts"
    source = file.read_text()
    marker = "// cloud-integrations: native verified session bootstrap"
    if marker in source:
        return

    start = source.index("async function initialize(")
    stop = source.index("\nasync function fetchSessionInfo()", start)
    if "Object.assign(session.user, getSessionFromCookies())" not in source[start:stop]:
        raise ValueError("Pinned Insights session initialization changed; review the adapter")
    source = source[:start] + f"""async function initialize(force: boolean = false) {{
	if (session.initialized && !force) return
	{marker}
	await Promise.all([
		fetchSiteInfo(),
		fetchSessionInfo().catch(() => resetSession()),
	])
	session.initialized = true
}}
""" + source[stop:]

    guard = "\tif (!session.isLoggedIn) return\n"
    if source.count(guard) != 1:
        raise ValueError("Pinned Insights session guard changed; review the adapter")
    source = source.replace(guard, "")
    source, count = re.subn(
        r"\nfunction getSessionFromCookies\(\) \{.*?\n\}\n", "", source, flags=re.DOTALL
    )
    if count != 1:
        raise ValueError("Pinned Insights cookie reader changed; review the adapter")
    file.write_text(source)


if __name__ == "__main__":
    patch(sys.argv[1])
