"""Socket.IO Origin forwarding in the ERP nginx template.

Frappe 16 rejects a realtime socket when the Origin host differs from the Host.
Browsers omit Origin on same-origin GET (the Socket.IO handshake), and the
pinned official template forces Origin to the internal site name. The template
must fill in the site's own origin only when Origin is absent and pass any
browser-supplied Origin unchanged, so cross-site sockets are still refused.
"""
from pathlib import Path
import re
import unittest

TEMPLATE = (Path(__file__).resolve().parents[1] / 'deployment/erp/frappe.conf.template').read_text()


class RealtimeOriginTests(unittest.TestCase):
    def test_origin_is_filled_in_only_when_absent(self):
        block = re.search(r'map \$http_origin \$socketio_origin \{(.*?)\}', TEMPLATE, re.S)
        self.assertIsNotNone(block)
        rules = dict(line.split(None, 1) for line in
                     (l.strip().rstrip(';') for l in block.group(1).splitlines()) if line)
        self.assertEqual(rules, {'""': '$proxy_x_forwarded_proto://$host', 'default': '$http_origin'})

    def test_socketio_location_uses_it_and_keeps_host(self):
        location = re.search(r'location /socket\.io \{(.*?)\n\t\}', TEMPLATE, re.S).group(1)
        self.assertIn('proxy_set_header Origin $socketio_origin;', location)
        self.assertIn('proxy_set_header Host $host;', location)
        self.assertNotIn('FRAPPE_SITE_NAME_HEADER}://', TEMPLATE.replace('${', '{'))
        self.assertEqual(len(re.findall(r'proxy_set_header Origin', TEMPLATE)), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
