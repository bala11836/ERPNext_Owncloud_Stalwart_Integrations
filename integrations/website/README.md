# Company front page (`website`)

## Purpose
A small static front page for the company's public address. It is always
reachable, whether or not anyone is signed in: a white page with an original
pencil drawing of a tunnel construction site that is drawn stroke by stroke in
four batches, the company logo, "Launching soon..." typed letter by letter, and
a plain "Employee Zone" link to the staff sign-in. It has no scripts that call
a server, no cookies and no access to business data.

## Contents
- `site/index.html`: the page (tenant-neutral: names, logo and link are filled
  from the private runtime profile at render time).
- `nginx-default.conf`: the web server block (port 8080, strict security
  headers, nothing but static files).
- `deployment/stacks/website.compose.json`: the pinned, read-only nginx container.
- `deployment/production/website.traefik.yaml`: production routes for
  `www.example.com` and a redirect of the bare domain to it.
- The test site serves the same page at the exact front path `/` of the test
  host plus its assets under `/front/` (`website_front_page` in the ingress
  profile), but only to visitors without an ERP session: once signed in, `/`
  is the portal, as on a production ERP host (P63). The gateway decides by the
  ERP's own sign-in cookie (`system_user=yes`); signing out clears it, so the
  front page comes back. Every other path still goes to the portal. The portal's
  sign-in return address and Home button stay `/place_holder`; the page then
  shows the clean address `/` in the address bar.

## Requirements
Docker with the workspace network, the repository's renderer
(`tools/prepare_runtime.py`, project `website`), and a proxy that can issue
certificates for the hosts. DNS for `www` and the bare domain must point at the
proxy before the production route is installed.

## Reuse
Take `integrations/website/`, the stack and mount entries, and the renderer's
`brand_website` step. Use it for any tenant: only the private profile changes.

## Configuration
Private profile keys (never in Git; for Mail, `favicon_url` may point at this page's `/front/favicon.svg`): `projects` includes `website`,
`website_title`, `website_name` (page title and logo text), `website_zone_url`
(a path or https URL; default the ERP host), `company_logo`,
`website_tagline` (default `Launching soon...`; empty hides it),
`website_zone_label` (default `Employee Zone`), `website_zone_style` (`text`
top left, default, or `badge`: a small button in the top-left corner like the
TEST SITE badge), `website_zone_color` (`#RRGGBB`, the badge colour) and
`website_art` (`pencil`, the default drawing, or `flower`: a flower and a bee
drawn line by line, then coloured, after the owner's sketch),
`company_favicon_dir` (SVG and PNG 16, 32, 48, 180, 192, 512). Without them the
page shows neutral placeholders. On production add the network alias
`website-web-production` through `extra_networks` and install the route file
with `example.com` replaced by the real domain. The drawing itself is generated
by a script that is kept with the tenant's private assets.

## Tests
`tests/test_website.py`: rendering with and without branding, link and text
validation, neutral public page, route files and the test front-page route.

## Licenses
The page, drawing and configuration are part of this repository
(AGPL-3.0-or-later). nginx is BSD-2-Clause. The tenant's logo and favicons are
the tenant's own and are not stored here.

## AI-assisted development
Written with AI assistance (Anthropic's Claude) and reviewed and accepted by
the owner, like the rest of this repository.

The Employee Zone link pulses at once after the first click and ignores further clicks until the page changes: the sign-in hops can take seconds (about three on the test site), and a second click used to cancel the first request.
