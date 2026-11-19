#!/usr/bin/env python3
"""Apply the declared pinned Insights frontend adapter before compiling it.

Identity comes from the native authenticated API. Parent-domain presentation
cookies can collide between production and test and are never authorization.
"""
from pathlib import Path
import re
import sys


def patch(root):
    file=Path(root)/'frontend/src/stores/sessionStore.ts'
    text=file.read_text()
    marker='// cloud-integrations: native verified session bootstrap'
    if marker in text:return
    pattern=r'\t\tObject\.assign\(user\.value, getSessionFromCookies\(\)\)\s*isLoggedIn\.value && \(await fetchSessionInfo\(\)\)\s*initialized\.value = true'
    replacement='''\t\t// cloud-integrations: native verified session bootstrap
\t\ttry {
\t\t\tconst verified: SessionUser = await api.fetchUserInfo()
\t\t\tObject.assign(user.value, { ...verified,
\t\t\t\tis_admin: Boolean(verified.is_admin), is_user: Boolean(verified.is_user),
\t\t\t\tis_v2_user: Boolean(verified.is_v2_user) })
\t\t} catch {
\t\t\tObject.assign(user.value, emptyUser)
\t\t}
\t\tinitialized.value = true'''
    text,count=re.subn(pattern,lambda _:replacement,text)
    if count!=1:raise ValueError('Pinned Insights session source changed; review the adapter')
    file.write_text(text)


if __name__=='__main__':patch(sys.argv[1])
