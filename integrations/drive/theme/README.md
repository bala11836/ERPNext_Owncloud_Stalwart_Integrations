# Drive web theme (`cloud`)

Tenant-neutral theme for the ownCloud web client (oCIS), derived from the
theme the oCIS release serves (`themes/owncloud/theme.json`, ownCloud web,
Apache-2.0; its notices apply to the derived file). Changes: the sign-in and
sign-in callback page ("Logging you in...") has a plain white background and
no logo (`assets/plain.svg`, `assets/blank.svg`), and the product name and
slogan under it are neutral. Everything else, including the top bar and
favicon, still uses the upstream theme assets. The renderer copies this folder
to Drive's web assets (`web/assets/themes/cloud/`) and points the web client
at it; oCIS reads the web configuration at start, so a theme switch needs an
oCIS restart (then restart the collaboration service, keeping its networks).

The background image path must be root-relative (`/themes/cloud/...`): the web client sets it in a CSS variable used by a stylesheet under `/assets/`, so a relative path resolves to `/assets/themes/...`, which returns the app's HTML (the upstream photo never loaded for the same reason and only the dark base colour showed).
