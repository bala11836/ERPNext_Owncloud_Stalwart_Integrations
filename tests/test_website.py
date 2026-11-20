"""The company front page: tenant-neutral source, private branding at render time, routes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from prepare_ingress import prepare as ingress  # noqa: E402
from prepare_runtime import prepare  # noqa: E402
from render_runtime import FAVICON_FILES  # noqa: E402

HOSTS = {k: ("test.example.net" if k == "erp" else "test-" + k + ".example.net")
         for k in ["erp", "sso", "drive", "office", "mail", "dms", "respond"]}


def profile(**extra):
    base = {"instance": "web-test", "tier": "test", "domain": "example.net", "hosts": HOSTS,
            "network": "isolated-workspace", "network_subnet": "10.44.0.0/24",
            "erp_image": "example/erp:test", "projects": ["website"]}
    base.update(extra)
    return base


def render(**extra):
    folder = tempfile.mkdtemp()
    output = Path(folder) / "runtime"
    prepare(ROOT, output, profile(**extra))
    return output


class WebsiteModule(unittest.TestCase):
    def test_public_source_is_tenant_neutral_and_static(self):
        page = (ROOT / "integrations/website/site/index.html").read_text()
        for token in ("__SITE_TITLE__", "__SITE_NAME__", "__EMPLOYEE_ZONE_URL__"):
            self.assertIn(token, page)
        self.assertNotIn("sriramki", page.lower())
        self.assertNotIn("unsplash", page.lower())          # our own drawing, no photo credit
        self.assertIn("text-transform: uppercase", page)     # EMPLOYEE / ZONE in capitals
        self.assertIn("Launching soon...", page)
        self.assertNotIn("fetch(", page)                     # no server calls
        conf = (ROOT / "integrations/website/nginx-default.conf").read_text()
        self.assertIn("listen 8080", conf)
        self.assertIn("default-src 'none'", conf)

    def test_branding_comes_from_the_private_profile(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "logo.svg").write_text("<svg id='tenant-logo'/>")
        favicons = folder / "fav"
        favicons.mkdir()
        for name in FAVICON_FILES:
            (favicons / name).write_bytes(b"tenant:" + name.encode())
        output = render(website_title="Acme", website_name="Acme Ltd", website_zone_url="/place_holder",
                        company_logo=str(folder / "logo.svg"), company_favicon_dir=str(favicons))
        site = output / "mounts/website_web_0"
        page = (site / "index.html").read_text()
        self.assertIn("<title>Acme</title>", page)
        self.assertIn('alt="Acme Ltd"', page)
        self.assertIn('href="/place_holder"', page)
        self.assertEqual((site / "logo.svg").read_text(), "<svg id='tenant-logo'/>")
        for name in FAVICON_FILES:
            self.assertEqual((site / name).read_bytes(), b"tenant:" + name.encode())
        compose = json.loads((output / "compose/website.json").read_text())["services"]["web"]
        self.assertIn("@sha256:", compose["image"])
        self.assertTrue(compose["read_only"])
        self.assertEqual(compose["networks"]["workspace"]["aliases"], ["website-web"])
        self.assertTrue((output / "mounts/website_web_1").is_file())

    def test_neutral_defaults_without_branding(self):
        output = render()
        site = output / "mounts/website_web_0"
        page = (site / "index.html").read_text()
        self.assertIn("<title>Welcome</title>", page)
        self.assertIn('href="https://test.example.net/"', page)   # the ERP host: staff sign-in
        self.assertTrue((site / "logo.svg").is_file())
        for name in FAVICON_FILES:
            self.assertTrue((site / name).is_file(), name)

    def test_unsafe_profile_values_are_refused(self):
        for key, value in (("website_zone_url", "javascript:alert(1)"), ("website_zone_url", "//evil.example"),
                           ("website_zone_url", "https://a.example/ x"), ("website_title", "<script>")):
            with self.assertRaises(ValueError, msg=key + "=" + value):
                render(**{key: value})

    def test_production_routes_serve_www_and_redirect_the_bare_domain(self):
        route = yaml.safe_load((ROOT / "deployment/production/website.traefik.yaml").read_text())["http"]
        routers = route["routers"]
        self.assertEqual(routers["website-www"]["rule"], "Host(`www.example.com`)")
        self.assertEqual(routers["website-www"]["tls"]["certResolver"], "letsencrypt")
        self.assertEqual(routers["website-www-http"]["middlewares"], ["website-https"])
        self.assertEqual(routers["website-apex"]["rule"], "Host(`example.com`)")
        self.assertEqual(routers["website-apex"]["middlewares"], ["website-to-www"])
        self.assertEqual(routers["website-apex-http"]["middlewares"], ["website-to-www"])
        redirect = route["middlewares"]["website-to-www"]["redirectRegex"]
        self.assertEqual(redirect["replacement"], "https://www.example.com/${1}")
        self.assertTrue(redirect["permanent"])
        self.assertEqual(route["services"]["website"]["loadBalancer"]["servers"][0]["url"],
                         "http://website-web-production:8080")

    def test_test_front_page_route_sits_above_the_portal_route_and_is_opt_in(self):
        http = ingress(ROOT, {"hosts": HOSTS, "ingress_prefix": "isolated", "website_front_page": True})["http"]
        front = http["routers"]["isolated-website-front"] if "isolated-website-front" in http["routers"] else \
            next(v for k, v in http["routers"].items() if k.endswith("website-front"))
        portal = next(v for k, v in http["routers"].items() if k.endswith("-erp") or k == "isolated-erp")
        self.assertEqual(front["rule"], "Host(`test.example.net`) && Path(`/`)")
        self.assertGreater(front["priority"], portal["priority"])
        self.assertNotIn("middlewares", front)               # public page: no sign-in middleware
        plain = ingress(ROOT, {"hosts": HOSTS, "ingress_prefix": "isolated"})["http"]["routers"]
        self.assertFalse([k for k in plain if k.endswith("website-front")])


if __name__ == "__main__":
    unittest.main()
