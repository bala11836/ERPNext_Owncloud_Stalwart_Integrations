"""Crippled test data: scrambling, 60-day cut, placeholders, kept accounts."""
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import cripple_snapshot as c  # noqa: E402
from restore_test_data import require_crippled_snapshot  # noqa: E402
import test_refresh_worker as worker  # noqa: E402

CUTOFF = datetime(2026, 9, 20, tzinfo=timezone.utc)


class Scrambling(unittest.TestCase):
    def test_deterministic_within_one_key_and_different_across_keys(self):
        one, same, other = c.Scrambler('k1'), c.Scrambler('k1'), c.Scrambler('k2')
        for kind in c.SPEC:
            self.assertEqual(one.value(kind, 'Ravi Steels'), same.value(kind, 'Ravi Steels'))
        self.assertNotEqual(one.value('email', 'ravi@example.com'), other.value('email', 'ravi@example.com'))
        self.assertEqual(len(c.Scrambler().key), 64)

    def test_fakes_never_contain_the_original_and_keep_their_shape(self):
        s = c.Scrambler('key')
        original = 'Ravi Kumar 9848012345 ravi@steels.example ABCDE1234F'
        values = {kind: s.value(kind, original) for kind in c.SPEC}
        for value in values.values():
            for piece in ['Ravi Kumar', '9848012345', 'steels', 'ABCDE1234F']:
                self.assertNotIn(piece, value)
        self.assertRegex(values['email'], r'^user-[0-9a-f]{10}@example\.invalid$')
        self.assertRegex(values['phone'], r'^\+91 1\d{9}$')
        self.assertRegex(values['pan'], r'^ZZ[A-Z]{3}\d{4}Z$')
        self.assertRegex(values['gstin'], r'^99ZZ[A-Z]{3}\d{4}Z1ZZ$')
        self.assertRegex(values['aadhaar'], r'^9999\d{8}$')
        self.assertRegex(values['ifsc'], r'^TEST0\d{6}$')
        self.assertRegex(values['account'], r'^000\d{9}$')
        self.assertEqual(s.value('text', original), c.PLACEHOLDER_TEXT)

    def test_sql_expression_mirrors_every_python_part(self):
        expression = c.mariadb_expression('pan', '`pan`')
        self.assertIn("SHA2(CONCAT(@ck,'|',`pan`),256)", expression)
        self.assertIn('ELT(MOD(CONV(SUBSTRING(', expression)
        self.assertEqual(c.mariadb_expression('text', '`x`'), "'" + c.PLACEHOLDER_TEXT + "'")
        self.assertEqual(c.sql_literal("O'Brien\\"), "'O''Brien\\\\'")


class Classification(unittest.TestCase):
    def test_personal_fields(self):
        cases = {('email_id', 'Data', 'Email'): 'email', ('mobile_no', 'Data', ''): 'phone',
                 ('phone', 'Phone', ''): 'phone', ('pan', 'Data', ''): 'pan', ('gstin', 'Data', ''): 'gstin',
                 ('tax_id', 'Data', ''): 'gstin', ('aadhaar_number', 'Data', ''): 'aadhaar',
                 ('ifsc_code', 'Data', ''): 'ifsc', ('bank_account_no', 'Data', ''): 'account',
                 ('address_line1', 'Data', ''): 'address', ('city', 'Data', ''): 'city',
                 ('pincode', 'Data', ''): 'pincode', ('supplier_name', 'Data', ''): 'company',
                 ('employee_name', 'Data', ''): 'person', ('first_name', 'Data', ''): 'person',
                 ('father_name', 'Data', ''): 'person', ('contact_name', 'Data', ''): 'person',
                 ('title', 'Data', ''): 'token', ('username', 'Data', ''): 'token',
                 ('remarks', 'Small Text', ''): 'text', ('content', 'Text Editor', ''): 'text',
                 ('recipients', 'Code', ''): 'email', ('date_of_birth', 'Date', ''): 'date',
                 ('json', 'JSON', ''): 'null'}
        for (name, kind, options), expected in cases.items():
            self.assertEqual(c.category(name, kind, options), expected, name)

    def test_business_and_reference_fields_are_kept(self):
        for name, kind in [('item_name', 'Data'), ('naming_series', 'Select'), ('attached_to_name', 'Data'),
                           ('reference_name', 'Data'), ('grand_total', 'Currency'), ('posting_date', 'Date'),
                           ('account_category_name', 'Data'), ('item_group_name', 'Data'), ('cost_center_name', 'Data'),
                           ('warehouse_name', 'Data'), ('shift_type', 'Link'),
                           ('script', 'Code'), ('reference_doctype', 'Data'), ('account_name', 'Data')]:
            self.assertIsNone(c.category(name, kind), name)


def meta():
    doctypes = {name: {'istable': False, 'issingle': False, 'is_submittable': False}
                for name in ['Sales Invoice', 'Customer', 'User', 'File', 'Version', 'DocType', 'Company', 'Contact',
                             'Salary Slip', 'Item']}
    doctypes['Sales Invoice']['is_submittable'] = True
    doctypes['Salary Slip']['is_submittable'] = True
    doctypes['Sales Invoice Item'] = {'istable': True, 'issingle': False, 'is_submittable': False}
    doctypes['Dynamic Link'] = {'istable': True, 'issingle': False, 'is_submittable': False}
    fields = [('Sales Invoice', 'customer', 'Link', 'Customer'), ('Sales Invoice', 'customer_name', 'Data', ''),
              ('Sales Invoice', 'remarks', 'Small Text', ''), ('Sales Invoice', 'items', 'Table', 'Sales Invoice Item'),
              ('Sales Invoice', 'contact_email', 'Data', 'Email'), ('Sales Invoice', 'grand_total', 'Currency', ''),
              ('Customer', 'customer_name', 'Data', ''), ('Customer', 'mobile_no', 'Data', 'Phone'),
              ('Contact', 'links', 'Table', 'Dynamic Link'), ('Contact', 'email_id', 'Data', 'Email'),
              ('Dynamic Link', 'link_doctype', 'Link', 'DocType'), ('Dynamic Link', 'link_name', 'Dynamic Link', 'link_doctype'),
              ('User', 'email', 'Data', 'Email'), ('User', 'first_name', 'Data', ''), ('User', 'user_image', 'Attach Image', ''),
              ('File', 'file_name', 'Data', ''), ('File', 'attached_to_name', 'Data', ''),
              ('DocType', 'description', 'Small Text', ''), ('Company', 'email', 'Data', 'Email'),
              ('Salary Slip', 'gross_pay', 'Currency', ''), ('Salary Slip', 'employee_name', 'Data', ''),
              ('Item', 'item_name', 'Data', '')]
    columns = {'tabSales Invoice': {'name', 'creation', 'posting_date', 'owner', 'modified_by', 'customer', 'customer_name',
                                    'remarks', 'contact_email', 'grand_total', '_assign'},
               'tabSales Invoice Item': {'name', 'parent', 'parenttype', 'creation'},
               'tabCustomer': {'name', 'creation', 'customer_name', 'mobile_no', 'owner', 'modified_by'},
               'tabContact': {'name', 'creation', 'email_id'},
               'tabDynamic Link': {'name', 'parent', 'parenttype', 'link_doctype', 'link_name'},
               'tabUser': {'name', 'email', 'first_name', 'user_image', 'creation'},
               'tabFile': {'name', 'creation', 'file_name', 'file_url', 'is_private', 'is_folder', 'attached_to_doctype',
                           'attached_to_name', 'content_hash'},
               'tabVersion': {'name', 'creation', 'data'}, 'tabDocType': {'name', 'description', 'modified_by'},
               'tabCompany': {'name', 'email'}, 'tabSalary Slip': {'name', 'creation', 'gross_pay', 'employee_name'},
               'tabItem': {'name', 'item_name', 'creation'}}
    return {'doctypes': doctypes, 'fields': fields, 'columns': columns}


class ErpPlan(unittest.TestCase):
    def setUp(self):
        self.plan = c.erp_plan(meta(), CUTOFF, ['Tester@Example.com'], 'k' * 64)
        self.sql = '\n'.join(self.plan)

    def test_logs_are_wiped_and_transactions_cut_to_the_window(self):
        self.assertIn('DELETE FROM `tabVersion`', self.plan)
        self.assertIn("DELETE FROM `tabSales Invoice` WHERE creation < '2026-09-20 00:00:00'", self.plan)
        self.assertIn("DELETE FROM `tabSalary Slip` WHERE creation < '2026-09-20 00:00:00'", self.plan)
        self.assertNotIn('DELETE FROM `tabItem` WHERE creation', self.sql)
        self.assertIn("DELETE c FROM `tabSales Invoice Item` c LEFT JOIN `tabSales Invoice` p ON p.name=c.parent "
                      "WHERE c.parenttype='Sales Invoice' AND p.name IS NULL", self.plan)

    def test_old_parties_are_pruned_unless_still_referenced(self):
        prune = next(s for s in self.plan if s.startswith('DELETE FROM `tabCustomer`'))
        self.assertIn("creation < '2026-09-20 00:00:00'", prune)
        self.assertIn('SELECT `customer` FROM `tabSales Invoice`', prune)

    def test_personal_fields_are_scrubbed_and_framework_records_are_not(self):
        self.assertTrue(any(s.startswith('UPDATE `tabSales Invoice` SET `remarks`=') for s in self.plan))
        self.assertTrue(any(s.startswith('UPDATE `tabCustomer` SET `mobile_no`=CONCAT(') for s in self.plan))
        self.assertTrue(any(s.startswith('UPDATE `tabSalary Slip` SET `gross_pay`=ROUND(RAND()') for s in self.plan))
        self.assertIn('UPDATE `tabSales Invoice` SET `_assign`=NULL WHERE `_assign` IS NOT NULL', self.plan)
        for untouched in ['UPDATE `tabDocType` SET `description`', 'UPDATE `tabCompany` SET',
                          'UPDATE `tabItem` SET `item_name`', 'SET `grand_total`', 'SET `attached_to_name`=CONCAT']:
            self.assertNotIn(untouched, self.sql)

    def test_kept_accounts_stay_real(self):
        user_updates = [s for s in self.plan if s.startswith('UPDATE `tabUser` SET') and '/files/file-' not in s]
        self.assertTrue(user_updates)
        for statement in user_updates:
            self.assertIn("LOWER(name) NOT IN ('administrator','guest','tester@example.com')", statement)
        insert = next(s for s in self.plan if s.startswith("INSERT INTO `_cripple_map` SELECT 'User'"))
        self.assertIn("NOT IN ('administrator','guest','tester@example.com')", insert)

    def test_unique_columns_get_collision_proof_fakes(self):
        data = meta()
        data['unique'] = {('tabCustomer', 'mobile_no'), ('tabUser', 'first_name'), ('tabSalary Slip', 'employee_name'),
                          ('tabSales Invoice', 'remarks')}
        sql = '\n'.join(c.erp_plan(data, CUTOFF, [], 'k' * 64))
        first = next(s for s in sql.split('\n') if s.startswith('UPDATE `tabUser` SET `first_name`='))
        self.assertIn(",57,8)", first)             # hex suffix: unique despite the small name pool
        slip = next(s for s in sql.split('\n') if s.startswith('UPDATE `tabSalary Slip` SET `employee_name`='))
        self.assertIn('SUBSTRING(SHA2(CONCAT(@ck,\'|\',`employee_name`),256),57,8)', slip)

    def test_renames_reach_every_reference(self):
        self.assertIn("UPDATE `tabSales Invoice` t JOIN `_cripple_map` m ON m.dt='Customer' AND m.old=t.`customer` "
                      'SET t.`customer`=m.new', self.plan)
        self.assertIn('UPDATE `tabDynamic Link` t JOIN `_cripple_map` m ON m.dt=t.`link_doctype` AND '
                      'm.old=t.`link_name` SET t.`link_name`=m.new', self.plan)
        self.assertIn("UPDATE `tabDocType` t JOIN `_cripple_map` m ON m.dt='User' AND m.old=t.`modified_by` "
                      'SET t.`modified_by`=m.new', self.plan)
        self.assertIn("UPDATE `tabCustomer` t JOIN `_cripple_map` m ON m.dt='Customer' AND m.old=t.name SET t.name=m.new",
                      self.plan)
        # Renames run after field scrubbing (so the keep filter sees real names).
        last_scrub = max(i for i, s in enumerate(self.plan)
                         if s.startswith('UPDATE `tabUser` SET') and '/files/file-' not in s)
        self.assertLess(last_scrub, self.plan.index('DROP TABLE IF EXISTS `_cripple_map`'))

    def test_file_names_and_attach_fields_are_remapped(self):
        self.assertTrue(any('INSERT IGNORE INTO `_cripple_files`' in s for s in self.plan))
        self.assertIn('UPDATE `tabUser` t JOIN `_cripple_files` m ON m.k=SHA2(t.`user_image`,256) SET t.`user_image`=m.new',
                      self.plan)
        self.assertTrue(any(s.startswith('DELETE FROM `tabFile` WHERE IFNULL(is_folder,0)=0 AND creation <')
                            for s in self.plan))


class Placeholders(unittest.TestCase):
    def test_pdf_is_well_formed(self):
        data = c.placeholder('.pdf', 'doc 1')
        self.assertTrue(data.startswith(b'%PDF-1.4') and data.rstrip().endswith(b'%%EOF'))
        offset = int(re.search(rb'startxref\n(\d+)', data).group(1))
        self.assertTrue(data[offset:].startswith(b'xref'))
        for number, entry in enumerate(re.findall(rb'(\d{10}) 00000 n', data), 1):
            self.assertTrue(data[int(entry):].startswith(str(number).encode() + b' 0 obj'))

    def test_png_and_office_files(self):
        png = c.placeholder('.JPG', 'x')
        self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
        length = struct.unpack('>I', png[8:12])[0]
        self.assertEqual(struct.unpack('>I', png[16 + length:20 + length])[0], zlib.crc32(png[12:16 + length]) & 0xffffffff)
        self.assertIn('word/document.xml', zipfile.ZipFile(io.BytesIO(c.placeholder('.docx', 'x'))).namelist())
        self.assertIn('xl/worksheets/sheet1.xml', zipfile.ZipFile(io.BytesIO(c.placeholder('.xlsx', 'x'))).namelist())
        self.assertIn(b'Placeholder', c.placeholder('.csv', 'x'))

    def test_each_label_gives_unique_bytes(self):
        for extension in ['.pdf', '.png', '.docx', '.xlsx', '.txt']:
            self.assertNotEqual(c.placeholder(extension, 'a'), c.placeholder(extension, 'b'))


def write_node(space, identifier, values, directory=False):
    base = space / 'nodes' / c.split_id(identifier)
    base.parent.mkdir(parents=True, exist_ok=True)
    if directory:
        base.mkdir(exist_ok=True)
    Path(str(base) + '.mpk').write_bytes(c.pack({'user.ocis.id': identifier.encode(), **values}))
    return base


class Drive(unittest.TestCase):
    def test_tree_is_cut_scrambled_and_consistent(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ['search', 'thumbnails', 'nats', 'storage/users/uploads/partial']:
                (root / name).mkdir(parents=True)
            space = root / 'storage/users/spaces/aa/aaaaaa-0000-0000-0000-000000000001'
            space_id = 'aaaaaaaa-0000-0000-0000-000000000001'
            folder_id, new_id, old_id = ('bbbbbbbb-0000-0000-0000-000000000002', 'cccccccc-0000-0000-0000-000000000003',
                                         'dddddddd-0000-0000-0000-000000000004')
            root_dir = write_node(space, space_id, {'user.ocis.type': b'2', 'user.ocis.space.name': b'Ravi Kumar',
                                                    'user.ocis.space.alias': b'personal/ravi'}, directory=True)
            folder_dir = write_node(space, folder_id, {'user.ocis.type': b'2', 'user.ocis.name': b'Ravi Steels invoices',
                                                       'user.ocis.parentid': space_id.encode()}, directory=True)
            (root_dir / 'Ravi Steels invoices').symlink_to(os.path.relpath(folder_dir, root_dir))
            blobs = {}
            for identifier, name, when, blob in [(new_id, 'Aadhaar Ravi.pdf', '2026-11-01T10:00:00.1Z', 'eeeeeeee-0000-0000-0000-000000000005'),
                                                 (old_id, 'Old PAN Ravi.jpg', '2026-01-01T10:00:00.1Z', 'ffffffff-0000-0000-0000-000000000006')]:
                base = write_node(space, identifier, {'user.ocis.type': b'1', 'user.ocis.name': name.encode(),
                    'user.ocis.parentid': folder_id.encode(), 'user.ocis.mtime': when.encode(),
                    'user.ocis.blobid': blob.encode(), 'user.ocis.blobsize': b'11', 'user.ocis.cs.crc32': b'x',
                    'user.ocis.tags': b'Ravi'})
                (folder_dir / name).symlink_to(os.path.relpath(base, folder_dir))
                path = space / 'blobs' / c.split_id(blob)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'REAL SECRET')
                blobs[identifier] = path
            revision = Path(str(space / 'nodes' / c.split_id(new_id)) + '.REV.2026-10-01T00:00:00Z')
            revision.write_bytes(b'REAL SECRET')
            orphan = space / 'blobs' / c.split_id('99999999-0000-0000-0000-000000000009')
            orphan.parent.mkdir(parents=True, exist_ok=True)
            orphan.write_bytes(b'REAL SECRET')
            (space / 'trash').mkdir()
            (space / 'trash' / 'gone').write_bytes(b'REAL SECRET')

            report = c.cripple_drive(root, CUTOFF, c.Scrambler('k'))

            self.assertEqual((report['kept_files'], report['removed_files'], report['renamed_folders']), (1, 1, 1))
            for name in ['search', 'thumbnails', 'nats']:
                self.assertFalse((root / name).exists())
            self.assertEqual(list((root / 'storage/users/uploads').iterdir()), [])
            self.assertFalse(revision.exists() or orphan.exists() or (space / 'trash' / 'gone').exists())
            self.assertFalse(blobs[old_id].exists())
            new_meta = c.unpack(Path(str(space / 'nodes' / c.split_id(new_id)) + '.mpk').read_bytes())
            blob = blobs[new_id].read_bytes()
            self.assertTrue(blob.startswith(b'%PDF'))
            self.assertEqual(new_meta['user.ocis.blobsize'], str(len(blob)).encode())
            self.assertEqual(new_meta['user.ocis.cs.md5'], hashlib.md5(blob).digest())
            self.assertEqual(new_meta['user.ocis.cs.sha1'], hashlib.sha1(blob).digest())
            self.assertEqual(new_meta['user.ocis.cs.adler32'], struct.pack('>I', zlib.adler32(blob)))
            self.assertNotIn('user.ocis.cs.crc32', new_meta)
            self.assertNotIn('user.ocis.tags', new_meta)
            new_name = new_meta['user.ocis.name'].decode()
            self.assertRegex(new_name, r'^file-[0-9a-f]{16}\.pdf$')
            folder_link = next(p for p in root_dir.iterdir() if p.is_symlink())
            self.assertRegex(folder_link.name, r'^Folder [0-9a-f]{8}$')
            self.assertEqual([p.name for p in folder_dir.iterdir() if p.is_symlink()], [new_name])
            # No original name or content survives anywhere in the tree.
            for path in root.rglob('*'):
                self.assertNotIn('Ravi', path.name)
                if path.is_file() and not path.is_symlink():
                    content = path.read_bytes()
                    self.assertNotIn(b'Ravi', content)
                    self.assertNotIn(b'REAL SECRET', content)

    def test_metadata_codec_round_trips_long_values(self):
        mapping = {f'user.ocis.key{i}': bytes([i]) * (300 if i == 3 else 5) for i in range(20)}
        self.assertEqual(c.unpack(c.pack(mapping)), mapping)


class Dms(unittest.TestCase):
    def test_documents_users_and_kept_accounts(self):
        rows = {'documents': [['7', 'application/pdf', 'Aadhaar Ravi.pdf', 'Ravi/aadhaar.pdf', 'Ravi/aadhaar.pdf']],
                'correspondents': [['1', 'Ravi Steels']], 'tags': [['2', 'Ravi']],
                'users': [['1', 'tester', 'tester@example.com'], ['2', 'ravi', 'ravi@example.com']]}
        placeholders = {}
        sql = '\n'.join(c.dms_statements(rows, c.Scrambler('k'), ['Tester@example.com'], placeholders))
        self.assertNotIn('Ravi', sql)
        self.assertNotIn('ravi@example.com', sql)
        self.assertIn("filename='0000007.pdf'", sql)
        self.assertIn("archive_filename='0000007.pdf'", sql)
        self.assertEqual(sql.count('UPDATE auth_user'), 1)
        self.assertIn('WHERE id=2', sql.split('UPDATE auth_user')[1])
        original = placeholders[('documents/originals', '0000007.pdf')]
        self.assertIn(f"checksum={c.sql_literal(hashlib.md5(original).hexdigest())}", sql)
        self.assertIn(('documents/thumbnails', '0000007.webp'), placeholders)
        self.assertLess(sql.index("filename='tmp-7'"), sql.index("filename='0000007.pdf'"))


class Boundaries(unittest.TestCase):
    def test_test_site_refuses_unscrambled_snapshots_once_required(self):
        require_crippled_snapshot({}, {'crippled': None})
        with self.assertRaises(ValueError):
            require_crippled_snapshot({'require_crippled': True}, {'crippled': None})
        require_crippled_snapshot({'require_crippled': True}, {'crippled': {'policy': 'crippled-v1'}})

    def test_code_refresh_resets_to_main_and_runs_the_profile_command(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            upstream, source = folder / 'upstream', folder / 'source'
            env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@example.com',
                       GIT_COMMITTER_NAME='t', GIT_COMMITTER_EMAIL='t@example.com')
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(upstream)], check=True)
            (upstream / 'a').write_text('1')
            subprocess.run(['git', '-C', str(upstream), 'add', 'a'], check=True)
            subprocess.run(['git', '-C', str(upstream), 'commit', '-qm', 'one'], check=True, env=env)
            subprocess.run(['git', 'clone', '-q', str(upstream), str(source)], check=True)
            (upstream / 'a').write_text('2')
            subprocess.run(['git', '-C', str(upstream), 'commit', '-qam', 'two'], check=True, env=env)
            marker = folder / 'deployed'
            config = {'source': str(source), 'code_refresh': {'command': ['sh', '-c', f'cp a {marker}']}}
            with open(folder / 'log', 'wb') as log:
                revision = worker.refresh_code(config, log)
            self.assertEqual(marker.read_text(), '2')
            self.assertEqual(revision, subprocess.check_output(['git', '-C', str(upstream), 'rev-parse', '--short', 'HEAD'],
                                                               text=True).strip())
            with self.assertRaises(RuntimeError), open(folder / 'log', 'wb') as log:
                worker.refresh_code({'source': str(source)}, log)


if __name__ == '__main__':
    unittest.main()
