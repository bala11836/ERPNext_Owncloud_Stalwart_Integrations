#!/usr/bin/env python3
"""Cripple a production snapshot ON PRODUCTION, before anything leaves it.

The test site gets a deliberately unrealistic copy (owner decision, 19 November
2026): strictly the last N days (default 60), every piece of personal
information replaced, and document contents replaced by placeholder files.
Numbers and balances need not add up.

- ERP (MariaDB) and DMS (PostgreSQL) dumps are loaded into throwaway database
  containers without a network, transformed there and dumped again. Production
  databases are only read by the normal export.
- Personal values are replaced by deterministic fakes derived from a random key
  that exists only during this run: the same original becomes the same fake
  within one export (links keep working), and there is no mapping to reverse.
- ERP attachments, DMS documents and Drive files are replaced by placeholder
  files of the same type; names are scrambled; revisions, trash, search indexes
  and thumbnails are dropped.
- Mail (a RocksDB store) cannot be scrambled offline, so it is not exported at
  all: test mailboxes start empty.
- Accounts listed in `keep_accounts` (members of the authentik group "Testers")
  keep their real login identity so they can sign in to test.
"""
import argparse
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import struct
import subprocess
import time
import uuid
import zipfile
import zlib
import io

POLICY = 'crippled-v1'
PLACEHOLDER_TEXT = 'Placeholder text (scrambled test copy).'
FIRST = ['Asha', 'Bhanu', 'Chitra', 'Deepak', 'Esha', 'Farhan', 'Gita', 'Hari', 'Indu', 'Jai', 'Kiran',
         'Lata', 'Mohan', 'Nisha', 'Om', 'Priya', 'Qasim', 'Ravi', 'Sita', 'Tara', 'Uma', 'Varun', 'Wasim',
         'Yamini', 'Zoya', 'Arun', 'Bina', 'Chetan', 'Divya', 'Ekta', 'Gopal', 'Hema']
LAST = ['Test', 'Sample', 'Example', 'Demo', 'Placeholder', 'Mock', 'Dummy', 'Trial']
COMPANY = ['Alpha', 'Bravo', 'Cedar', 'Delta', 'Ember', 'Falcon', 'Garnet', 'Harbor', 'Indigo', 'Juniper',
           'Kestrel', 'Lotus', 'Maple', 'Nimbus', 'Orchid', 'Pebble', 'Quartz', 'Raven', 'Saffron', 'Tulip',
           'Umber', 'Velvet', 'Willow', 'Yarrow', 'Zephyr', 'Aster', 'Birch', 'Coral', 'Dune', 'Fern', 'Glade', 'Heron']
ALPHABET = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
SUFFIX = ['Test Traders', 'Test Industries', 'Test Enterprises', 'Test Works', 'Test Supplies',
          'Test Agencies', 'Test Builders', 'Test Services']

# Categories derive every fake from the same hex digest h of (key | original).
# n(a, b) = int(h[a:b], 16). The SQL generator below mirrors these exactly.
SPEC = {
    'email': [('lit', 'user-'), ('hex', 0, 10), ('lit', '@example.invalid')],
    # +91 1... is never a real Indian mobile number.
    'phone': [('lit', '+91 1'), ('num', 10, 18, 1000000000, 9)],
    'pan': [('lit', 'ZZ'), ('pick', 18, 20, ALPHABET), ('pick', 20, 22, ALPHABET), ('pick', 22, 24, ALPHABET),
            ('num', 46, 52, 10000, 4), ('lit', 'Z')],
    'gstin': [('lit', '99ZZ'), ('pick', 18, 20, ALPHABET), ('pick', 20, 22, ALPHABET), ('pick', 22, 24, ALPHABET),
              ('num', 46, 52, 10000, 4), ('lit', 'Z1ZZ')],
    'aadhaar': [('lit', '9999'), ('num', 24, 32, 100000000, 8)],
    'ifsc': [('lit', 'TEST0'), ('num', 32, 38, 1000000, 6)],
    'account': [('lit', '000'), ('num', 38, 46, 1000000000, 9)],
    'person': [('pick', 0, 4, FIRST), ('lit', ' '), ('pick', 4, 8, LAST)],
    'company': [('pick', 0, 4, COMPANY), ('lit', ' '), ('pick', 4, 8, SUFFIX)],
    'address': [('num', 0, 4, 999, 0), ('lit', ' Test Street')],
    'city': [('lit', 'Testpur')],
    'pincode': [('lit', '999'), ('num', 0, 6, 1000, 3)],
    'token': [('lit', 'Test '), ('hex', 0, 8)],
    'unique': [('lit', 'Test '), ('hex', 0, 20)],
    'person-doc': [('pick', 0, 4, FIRST), ('lit', ' '), ('pick', 4, 8, LAST), ('lit', ' '), ('hex', 56, 64)],
    'company-doc': [('pick', 0, 4, COMPANY), ('lit', ' '), ('pick', 4, 8, SUFFIX), ('lit', ' '), ('hex', 56, 64)],
}


class Scrambler:
    """Deterministic within one run, irreversible across runs (the key is discarded)."""

    def __init__(self, key=None):
        self.key = key or secrets.token_hex(32)

    def digest(self, value):
        return hashlib.sha256((self.key + '|' + str(value)).encode('utf-8')).hexdigest()

    def value(self, category, original):
        if category == 'text':
            return PLACEHOLDER_TEXT
        h = self.digest(original)
        out = []
        for part in SPEC[category]:
            if part[0] == 'lit':
                out.append(part[1])
            elif part[0] == 'hex':
                out.append(h[part[1]:part[2]])
            elif part[0] == 'num':
                value = int(h[part[1]:part[2]], 16) % part[3]
                out.append(str(value).zfill(part[4]) if part[4] else str(value))
            elif part[0] == 'pick':
                out.append(part[3][int(h[part[1]:part[2]], 16) % len(part[3])])
        return ''.join(out)


def sql_literal(value):
    return "'" + str(value).replace('\\', '\\\\').replace("'", "''") + "'"


def mariadb_expression(category, column):
    """MariaDB expression equal to Scrambler.value(category, column) for @ck."""
    if category == 'text':
        return sql_literal(PLACEHOLDER_TEXT)
    h = f"SHA2(CONCAT(@ck,'|',{column}),256)"
    parts = []
    for part in SPEC[category]:
        if part[0] == 'lit':
            parts.append(sql_literal(part[1]))
        elif part[0] == 'hex':
            parts.append(f'SUBSTRING({h},{part[1] + 1},{part[2] - part[1]})')
        elif part[0] == 'num':
            number = f'MOD(CONV(SUBSTRING({h},{part[1] + 1},{part[2] - part[1]}),16,10),{part[3]})'
            parts.append(f"LPAD({number},{part[4]},'0')" if part[4] else f'CAST({number} AS CHAR)')
        elif part[0] == 'pick':
            words = ','.join(sql_literal(word) for word in part[3])
            parts.append(f'ELT(MOD(CONV(SUBSTRING({h},{part[1] + 1},{part[2] - part[1]}),16,10),{len(part[3])})+1,{words})')
    return 'CONCAT(' + ','.join(parts) + ')'


# ---------------------------------------------------------------- ERP policy
TEXT_TYPES = {'Text', 'Small Text', 'Long Text', 'Text Editor', 'HTML Editor', 'Markdown Editor', 'Signature'}
VALUE_TYPES = {'Data', 'Phone', 'Read Only', 'Autocomplete'}
# Framework, configuration and branding records: never scrubbed.
META = {'DocType', 'DocField', 'DocPerm', 'Custom DocPerm', 'Custom Field', 'Property Setter', 'Client Script',
        'Server Script', 'Report', 'Report Column', 'Report Filter', 'Print Format', 'Print Style', 'Print Heading',
        'Workspace', 'Workspace Link', 'Workspace Shortcut', 'Workspace Chart', 'Workspace Number Card',
        'Workspace Quick List', 'Workspace Custom Block', 'Page', 'Module Def', 'Web Form', 'Web Form Field',
        'Web Page', 'Website Settings', 'Website Theme', 'Email Template', 'Notification', 'Letter Head',
        'Number Card', 'Dashboard Chart', 'Dashboard', 'Workflow', 'Workflow State', 'Workflow Action Master',
        'Workflow Document State', 'Workflow Transition', 'Patch Log', 'Installed Application',
        'Installed Applications', 'Navbar Settings', 'Navbar Item', 'Portal Settings', 'System Settings', 'Role',
        'Role Profile', 'Module Profile', 'User Type', 'DocType Link', 'DocType Action', 'DocType State',
        'Form Tour', 'Form Tour Step', 'Onboarding Step', 'Module Onboarding', 'Kanban Board', 'Kanban Board Column',
        'List View Settings', 'Custom HTML Block', 'Translation', 'Company', 'Print Settings', 'Desktop Icon'}
# Logs and histories: wiped entirely on test.
WIPE = ['Version', 'Activity Log', 'Access Log', 'Error Log', 'Email Queue', 'Email Queue Recipient',
        'Notification Log', 'Route History', 'Deleted Document', 'Prepared Report', 'Integration Request',
        'Webhook Request Log', 'Data Import Log', 'Submission Queue', 'Scheduled Job Log', 'Unhandled Email',
        'Energy Point Log', 'Console Log', 'Document Follow', 'View Log', 'Transaction Log', 'Email Unsubscribe',
        'Data Import', 'OAuth Bearer Token', 'OAuth Authorization Code', 'Sessions']
# Not submittable, but transactional: cut to the window as well.
CUT_EXTRA = ['Communication', 'Comment', 'ToDo', 'Event', 'Note', 'Raven Message', 'Raven Mention',
             'Raven Message Reaction', 'Timesheet', 'Task', 'Issue', 'Attendance Request', 'Leave Application',
             'Employee Checkin', 'Opportunity', 'Lead', 'Prospect', 'Quotation', 'Project']
# Docnames that carry personal or customer names: renamed everywhere.
RENAME = {'Supplier': 'company-doc', 'Customer': 'company-doc', 'Lead': 'person-doc', 'Prospect': 'company-doc',
          'Contact': 'person-doc', 'Address': 'company-doc', 'Bank Account': 'company-doc',
          'Employee': 'person-doc', 'Sales Partner': 'company-doc', 'Sales Person': 'person-doc',
          'Shareholder': 'person-doc', 'Driver': 'person-doc'}
# Doctypes whose record names are the user's login: renamed with the User map.
USER_NAMED = ['Raven User', 'Notification Settings', 'Dashboard Settings', 'Energy Point Settings']
PARTIES = ['Supplier', 'Customer', 'Lead', 'Prospect', 'Contact', 'Address', 'Bank Account', 'Employee',
           'Sales Partner', 'Shareholder', 'Driver']
PAYROLL = {'Salary Slip', 'Salary Detail', 'Salary Structure Assignment', 'Additional Salary', 'Salary Structure',
           'Employee Incentive', 'Retention Bonus', 'Employee Advance', 'Gratuity', 'Employee Benefit Claim',
           'Employee Benefit Application', 'Employee Tax Exemption Declaration',
           'Employee Tax Exemption Proof Submission', 'Payroll Employee Detail', 'Employee'}
# Files attached to configuration/branding records survive the age cut.
KEEP_FILES_OF = META | {'Item', 'Item Group', 'Brand'}
# Explicit reference pairs not described as Dynamic Link in metadata.
REFERENCE_PAIRS = [('File', 'attached_to_doctype', 'attached_to_name'),
                   ('Comment', 'reference_doctype', 'reference_name'),
                   ('Communication', 'reference_doctype', 'reference_name'),
                   ('Communication Link', 'link_doctype', 'link_name'),
                   ('ToDo', 'reference_type', 'reference_name'),
                   ('DocShare', 'share_doctype', 'share_name'),
                   ('Dynamic Link', 'link_doctype', 'link_name'),
                   ('User Permission', 'allow', 'for_value'),
                   ('Event Participants', 'reference_doctype', 'reference_docname')]
NOT_PERSONAL = {'naming_series', 'item_name', 'item_group_name', 'account_name', 'warehouse_name', 'uom_name',
                'brand_name', 'cost_center_name', 'department_name', 'designation_name', 'holiday_list_name',
                'company_name', 'module_name', 'report_name', 'template_name', 'field_name', 'fieldname',
                'workflow_name', 'series_name', 'app_name', 'print_format_name', 'bank_name', 'tax_category',
                'territory_name', 'customer_group_name', 'supplier_group_name', 'price_list_name',
                'mode_of_payment', 'title_prefix', 'role_name', 'doctype_name', 'naming_by', 'currency_name',
                'country_name', 'state_name', 'activity_name', 'operation_name',
                # References remapped by the rename step, not scrubbed.
                'attached_to_name', 'attached_to_field', 'reference_name', 'reference_docname', 'link_name',
                'share_name', 'for_value', 'against_voucher', 'voucher_no', 'parent', 'docname', 'ref_docname'}
# Catch-all sweep over every text column: anything that still looks like an e-mail
# address, GSTIN or PAN (and is not one of this run's fakes) is replaced. Framework
# metadata tables are skipped; so are key and link columns, to keep references intact.
TEXTUAL = {'varchar', 'tinytext', 'text', 'mediumtext', 'longtext', 'json'}
SWEEP_SKIP_TABLES = {'DocType', 'DocField', 'DocPerm', 'Custom DocPerm', 'Patch Log', 'Installed Application',
                     'Module Def', 'Translation', 'Singles'}
SWEEP_SKIP_COLUMNS = {'name', 'parent', 'parenttype', 'parentfield', 'owner', 'modified_by', 'creation', 'modified',
                      'docstatus', 'idx', 'user', 'email', 'email_id', 'for_user', 'allow', 'for_value'}
SWEEP = [(r"[A-Za-z0-9._%+-]+@(?!example\.invalid)[A-Za-z0-9-]+\.[A-Za-z0-9.-]*[A-Za-z]", '@',
          'redacted@example.invalid'),
         (r'(?-i)\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b', None, '99ZZZZZ9999Z1ZZ'),
         (r'(?-i)\b[A-Z]{5}[0-9]{4}[A-Z]\b', None, 'ZZZZZ9999Z')]
SYSTEM_COLUMNS = ['_assign', '_liked_by', '_comments', '_seen', '_user_tags']
# A kept account (member of the test-access group) keeps ONLY its login identity: e-mail,
# username and name. Every other profile field is scrambled or cleared like anyone else's.
USER_IDENTITY = {'email', 'username', 'first_name', 'middle_name', 'last_name', 'full_name'}
# Personal or secret columns of tabUser that the generic classification does not recognise.
USER_CLEAR = ['location', 'last_ip', 'api_key', 'reset_password_key', 'github_username', 'google_username',
              'facebook_username', 'twitter_username', 'frappe_userid', 'office_365_username']


def category(fieldname, fieldtype, options=''):
    """Classify one field: a SPEC category, 'text', 'null', 'date', or None (keep)."""
    name = fieldname.lower()
    if fieldtype in TEXT_TYPES:
        return 'text'
    if fieldtype == 'JSON':
        return 'null'
    if fieldtype == 'Date':
        return 'date' if re.search(r'birth|dob|anniversary|marriage', name) else None
    if fieldtype == 'Code':
        return 'email' if name in {'recipients', 'cc', 'bcc', 'sender', 'reply_to'} else None
    if fieldtype not in VALUE_TYPES:
        return None
    if name in NOT_PERSONAL or name.endswith(('doctype', '_type')):
        return None
    if options == 'Email' or 'email' in name or name in {'sender', 'recipients', 'cc', 'bcc', 'reply_to'}:
        return 'email'
    if fieldtype == 'Phone' or options == 'Phone' or re.search(r'phone|mobile|whatsapp|fax|cell', name):
        return 'phone'
    if re.search(r'aadha?ar|uidai|(^|_)uid($|_)', name):
        return 'aadhaar'
    if 'gstin' in name or name in {'gst_number', 'gst_no', 'tax_id', 'gst_registration_number'}:
        return 'gstin'
    if re.search(r'(^|_)pan($|_)|pan_no|pan_number|pan_card', name):
        return 'pan'
    if re.search(r'ifsc|swift|iban|branch_code|micr', name):
        return 'ifsc'
    if re.search(r'account_no|account_number|bank_ac|acc_no|bank_account|(^|_)upi', name):
        return 'account'
    if re.search(r'pincode|pin_code|postal|zip', name):
        return 'pincode'
    if re.search(r'address|street|landmark|line1|line2|locality', name):
        return 'address'
    if re.search(r'(^|_)city|town|village|district', name):
        return 'city'
    if name == 'title' or name.endswith('_title') or name == 'username':
        return 'token'
    if re.search(r'supplier|customer|party|company|business|vendor|firm|lead|organi[sz]|trade|correspondent', name) \
            and 'name' in name:
        return 'company'
    # Only fields that hold a human's name: masters such as account, item or
    # category names are configuration, not personal data, and stay as they are.
    if re.search(r'(^|_)(first|middle|last|full|employee|contact|owner|holder|father|mother|spouse|guardian|'
                 r'nominee|person|signatory|driver|candidate|applicant|salesperson|sender|passport|nick)(_|$)', name) \
            and not name.endswith(('_type', '_category', '_group')):
        return 'person'
    return None


def quote(identifier):
    if '`' in identifier:
        raise ValueError('Unexpected identifier')
    return '`' + identifier + '`'


def table(doctype):
    return quote('tab' + doctype)


def erp_plan(meta, cutoff, keep_accounts, key):
    """SQL statements crippling one ERP database. `meta` is read from that database:
    doctypes {name: {istable, issingle, is_submittable}}, fields [(doctype, fieldname,
    fieldtype, options)], columns {table name: set(columns)}."""
    doctypes, fields, columns = meta['doctypes'], meta['fields'], meta['columns']
    unique = meta.get('unique', set())
    keep = sorted({account.casefold() for account in keep_accounts} | {'administrator', 'guest'})
    keep_sql = ','.join(sql_literal(account) for account in keep)
    cut = sql_literal(cutoff.strftime('%Y-%m-%d %H:%M:%S'))

    def present(doctype):
        return ('tab' + doctype) in columns

    def has(doctype, column):
        return column in columns.get('tab' + doctype, set())

    regular = {name for name, row in doctypes.items() if not row['istable'] and not row['issingle'] and present(name)}
    statements = [f'SET @ck={sql_literal(key)}', 'SET FOREIGN_KEY_CHECKS=0', "SET SESSION sql_mode=''"]
    # 1. Logs and histories.
    for doctype in WIPE:
        if present(doctype):
            statements.append(f'DELETE FROM {table(doctype)}')
    for extra in ['__UserSettings', '__global_search']:
        if extra in columns:
            statements.append(f'DELETE FROM {quote(extra)}')
    # 2. Strict window for transactions.
    transactions = sorted(name for name in regular if name not in META and has(name, 'creation') and (
        doctypes[name]['is_submittable'] or name in CUT_EXTRA
        or has(name, 'posting_date') or has(name, 'transaction_date')))
    for doctype in transactions:
        statements.append(f'DELETE FROM {table(doctype)} WHERE creation < {cut}')
    children = {}
    for doctype, fieldname, fieldtype, options in fields:
        if fieldtype in {'Table', 'Table MultiSelect'} and options and present(options) and doctype in regular:
            children.setdefault(doctype, set()).add(options)

    def drop_orphans(parents):
        for parent in parents:
            for child in sorted(children.get(parent, ())):
                statements.append(f'DELETE c FROM {table(child)} c LEFT JOIN {table(parent)} p ON p.name=c.parent '
                                  f'WHERE c.parenttype={sql_literal(parent)} AND p.name IS NULL')
    drop_orphans(transactions)
    # 3. Old parties not referenced by any remaining transaction.
    sources = set(transactions) | {child for parent in transactions for child in children.get(parent, ())}
    links, dynamic = [], []
    for doctype, fieldname, fieldtype, options in fields:
        if doctype in META or not has(doctype, fieldname):
            continue
        if fieldtype == 'Link' and options:
            links.append((doctype, fieldname, options))
        elif fieldtype == 'Dynamic Link' and options and has(doctype, options):
            dynamic.append((doctype, fieldname, options))
    for doctype, doctype_column, name_column in REFERENCE_PAIRS:
        if has(doctype, doctype_column) and has(doctype, name_column) and (doctype, name_column, doctype_column) not in dynamic:
            dynamic.append((doctype, name_column, doctype_column))
    parties = [party for party in PARTIES if present(party)]
    for party in parties:
        refs = [f'SELECT {quote(f)} FROM {table(d)} WHERE {quote(f)} IS NOT NULL'
                for d, f, o in links if o == party and d in sources]
        refs += [f'SELECT {quote(f)} FROM {table(d)} WHERE {quote(o)}={sql_literal(party)}'
                 for d, f, o in dynamic if d in sources]
        condition = f'creation < {cut}'
        if refs:
            condition += f' AND name NOT IN (SELECT * FROM ({" UNION ".join(refs)}) r)'
        statements.append(f'DELETE FROM {table(party)} WHERE {condition}')
    drop_orphans(parties)
    # 4. Attachments: inside the window and still attached (branding kept).
    if present('File'):
        keep_files = ','.join(sql_literal(name) for name in sorted(KEEP_FILES_OF))
        statements.append(f"DELETE FROM `tabFile` WHERE IFNULL(is_folder,0)=0 AND creation < {cut} "
                          f"AND IFNULL(attached_to_doctype,'') NOT IN ({keep_files})")
        for doctype in transactions + parties:
            statements.append(f'DELETE f FROM `tabFile` f LEFT JOIN {table(doctype)} d ON d.name=f.attached_to_name '
                              f"WHERE f.attached_to_doctype={sql_literal(doctype)} AND d.name IS NULL "
                              f'AND IFNULL(f.is_folder,0)=0')
    # 5. Field values.
    for doctype, fieldname, fieldtype, options in fields:
        if doctype in META or not has(doctype, fieldname) or doctypes.get(doctype, {}).get('issingle'):
            continue
        kind = category(fieldname, fieldtype, options)
        if kind is None and doctype in PAYROLL and fieldtype in {'Currency', 'Float', 'Int', 'Percent'}:
            kind = 'random-amount'
        if kind is None:
            continue
        if ('tab' + doctype, fieldname) in unique and kind in {'person', 'company', 'address', 'city', 'pincode', 'token'}:
            kind = {'person': 'person-doc', 'company': 'company-doc'}.get(kind, 'unique')
        column = quote(fieldname)
        where = f'WHERE {column} IS NOT NULL'
        if kind not in {'random-amount', 'date'}:
            where += f" AND {column}<>''"
        if doctype == 'User' and fieldname in USER_IDENTITY:
            # Only the login identity of kept accounts stays real; all other profile fields change for everyone.
            where += f' AND LOWER(name) NOT IN ({keep_sql})'
        if kind == 'null':
            value = 'NULL'
        elif kind == 'date':
            value = "'1990-01-01'"
        elif kind == 'random-amount':
            value = 'ROUND(RAND()*100000,2)'
        else:
            value = mariadb_expression(kind, column)
        statements.append(f'UPDATE {table(doctype)} SET {column}={value} {where}')
    for column in USER_CLEAR:
        if has('User', column):
            statements.append(f'UPDATE `tabUser` SET {quote(column)}=NULL WHERE {quote(column)} IS NOT NULL')
    if present('User Social Login'):
        # Provider user ids of accounts that are not kept; kept accounts need theirs to sign in.
        statements.append(f'DELETE FROM `tabUser Social Login` WHERE LOWER(parent) NOT IN ({keep_sql})')
    for name, cols in sorted(columns.items()):
        if not name.startswith('tab') or name[3:] in META:
            continue
        for column in SYSTEM_COLUMNS:
            if column in cols:
                statements.append(f'UPDATE {quote(name)} SET {quote(column)}=NULL WHERE {quote(column)} IS NOT NULL')
    # 6. Renames: parties and user accounts, applied to every reference.
    statements.append('DROP TABLE IF EXISTS `_cripple_map`')
    statements.append('CREATE TABLE `_cripple_map` (dt VARCHAR(140) NOT NULL, old VARCHAR(255) NOT NULL, '
                      'new VARCHAR(255) NOT NULL, PRIMARY KEY (dt, old)) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 '
                      'COLLATE=utf8mb4_unicode_ci')
    for doctype, kind in RENAME.items():
        if present(doctype):
            statements.append(f'INSERT INTO `_cripple_map` SELECT {sql_literal(doctype)}, name, '
                              f'{mariadb_expression(kind, "name")} FROM {table(doctype)}')
    if present('User'):
        statements.append(f"INSERT INTO `_cripple_map` SELECT 'User', name, {mariadb_expression('email', 'name')} "
                          f'FROM `tabUser` WHERE LOWER(name) NOT IN ({keep_sql})')
    for doctype in USER_NAMED:
        if present(doctype):
            statements.append(f"INSERT IGNORE INTO `_cripple_map` SELECT {sql_literal(doctype)}, old, new "
                              "FROM `_cripple_map` WHERE dt='User'")
    mapped = set(RENAME) | {'User'} | {d for d in USER_NAMED if present(d)}
    for doctype, fieldname, options in links:
        if options in mapped:
            statements.append(f'UPDATE {table(doctype)} t JOIN `_cripple_map` m ON m.dt={sql_literal(options)} '
                              f'AND m.old=t.{quote(fieldname)} SET t.{quote(fieldname)}=m.new')
    for doctype, fieldname, doctype_column in dynamic:
        statements.append(f'UPDATE {table(doctype)} t JOIN `_cripple_map` m ON m.dt=t.{quote(doctype_column)} '
                          f'AND m.old=t.{quote(fieldname)} SET t.{quote(fieldname)}=m.new')
    for name, cols in sorted(columns.items()):
        if not name.startswith('tab'):
            continue
        if {'parent', 'parenttype'} <= cols:
            statements.append(f'UPDATE {quote(name)} t JOIN `_cripple_map` m ON m.dt=t.parenttype AND m.old=t.parent '
                              'SET t.parent=m.new')
        for column in ('owner', 'modified_by'):
            if column in cols:
                statements.append(f"UPDATE {quote(name)} t JOIN `_cripple_map` m ON m.dt='User' "
                                  f'AND m.old=t.{quote(column)} SET t.{quote(column)}=m.new')
    if 'tabDefaultValue' in columns:
        statements.append("UPDATE `tabDefaultValue` t JOIN `_cripple_map` m ON m.dt='User' AND m.old=t.parent "
                          'SET t.parent=m.new')
    for doctype in sorted(mapped):
        if present(doctype):
            statements.append(f'UPDATE {table(doctype)} t JOIN `_cripple_map` m ON m.dt={sql_literal(doctype)} '
                              'AND m.old=t.name SET t.name=m.new')
    # 6b. Records named after a user's login (settings, preferences) follow the user rename.
    for name, cols in sorted(columns.items()):
        if name.startswith('tab') and 'name' in cols and 'parent' not in cols and name[3:] not in mapped \
                and name not in {'tabSingles'}:
            statements.append(f'UPDATE {quote(name)} t JOIN `_cripple_map` m ON m.dt=\'User\' AND m.old=t.name '
                              'SET t.name=m.new')
    # 6c. Catch-all sweep (see SWEEP above).
    skip_columns = set()
    for doctype, fieldname, options in links:
        skip_columns.add(('tab' + doctype, fieldname))
    for doctype, fieldname, doctype_column in dynamic:
        skip_columns.add(('tab' + doctype, fieldname))
    types = meta.get('types', {})
    # Links, owners and parents still holding a login that has no User record (deleted
    # users): the same deterministic fake as the rename map, so they stay consistent.
    key_columns = set(skip_columns) | {(name, column) for name, cols in columns.items() if name.startswith('tab')
                                       for column in ('owner', 'modified_by', 'parent') if column in cols}
    for table_name, column in sorted(key_columns):
        if types and types.get((table_name, column)) not in TEXTUAL:
            continue
        statements.append(f'UPDATE {quote(table_name)} SET {quote(column)}={mariadb_expression("email", quote(column))} '
                          f"WHERE {quote(column)} REGEXP '^[^@ ]+@[^@ ]+$' AND {quote(column)} NOT LIKE '%@example.invalid' "
                          f'AND LOWER({quote(column)}) NOT IN ({keep_sql})')
    for (table_name, column), data_type in sorted(types.items()):
        if (not table_name.startswith('tab') or table_name[3:] in SWEEP_SKIP_TABLES or data_type not in TEXTUAL
                or column in SWEEP_SKIP_COLUMNS or (table_name, column) in skip_columns
                or (table_name.startswith('tab_') or table_name.startswith('__'))):
            continue
        expression = quote(column)
        for pattern, probe, replacement in SWEEP:
            expression = f'REGEXP_REPLACE({expression},{sql_literal(pattern)},{sql_literal(replacement)})'
        statements.append(f'UPDATE {quote(table_name)} SET {quote(column)}={expression} WHERE {quote(column)} IS NOT NULL '
                          f"AND {quote(column)} REGEXP '@|[A-Za-z]{{5}}[0-9]{{4}}[A-Za-z]'")
    # 7. File URLs carry original file names: map them to scrambled names.
    statements.append('DROP TABLE IF EXISTS `_cripple_files`')
    statements.append('CREATE TABLE `_cripple_files` (k CHAR(64) NOT NULL PRIMARY KEY, old TEXT NOT NULL, '
                      'new VARCHAR(255) NOT NULL, is_private INT NOT NULL) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 '
                      'COLLATE=utf8mb4_unicode_ci')
    if present('File'):
        extension = ("IF(LOCATE('.',SUBSTRING_INDEX(file_url,'/',-1))>0 AND CHAR_LENGTH(SUBSTRING_INDEX(file_url,'.',-1))<=5,"
                     "CONCAT('.',LOWER(SUBSTRING_INDEX(file_url,'.',-1))),'')")
        statements.append("INSERT IGNORE INTO `_cripple_files` SELECT SHA2(file_url,256), file_url, "
                          "CONCAT(IF(IFNULL(is_private,0),'/private/files/','/files/'),'file-',"
                          f"SUBSTRING(SHA2(CONCAT(@ck,'|',file_url),256),1,16),{extension}), IFNULL(is_private,0) "
                          "FROM `tabFile` WHERE IFNULL(is_folder,0)=0 AND file_url LIKE '/%files/%'")
        statements.append("UPDATE `tabFile` f JOIN `_cripple_files` m ON m.k=SHA2(f.file_url,256) "
                          "SET f.file_url=m.new, f.file_name=SUBSTRING_INDEX(m.new,'/',-1), f.content_hash=NULL")
        if has('File', 'thumbnail_url'):
            statements.append('UPDATE `tabFile` SET thumbnail_url=NULL')
        statements.append("UPDATE `tabFile` SET file_url=NULL, file_name='external link' "
                          "WHERE IFNULL(is_folder,0)=0 AND file_url LIKE 'http%'")
    for doctype, fieldname, fieldtype, options in fields:
        if fieldtype in {'Attach', 'Attach Image'} and doctype not in META and has(doctype, fieldname) \
                and not doctypes.get(doctype, {}).get('issingle'):
            column = quote(fieldname)
            statements.append(f'UPDATE {table(doctype)} t JOIN `_cripple_files` m ON m.k=SHA2(t.{column},256) '
                              f'SET t.{column}=m.new')
            statements.append(f"UPDATE {table(doctype)} SET {column}=NULL WHERE {column} IS NOT NULL "
                              f"AND {column} NOT LIKE '/files/file-%' AND {column} NOT LIKE '/private/files/file-%'")
    return statements


# ------------------------------------------------------------- placeholders
def _pdf(label):
    text = ('Placeholder - scrambled test copy - ' + label).encode('latin-1', 'replace')
    text = text.replace(b'\\', b'').replace(b'(', b'').replace(b')', b'')
    stream = b'BT /F1 14 Tf 60 760 Td (' + text + b') Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R '
               b'/Resources << /Font << /F1 5 0 R >> >> >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    out = bytearray(b'%PDF-1.4\n')
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += str(number).encode() + b' 0 obj\n' + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 ' + str(len(objects) + 1).encode() + b'\n0000000000 65535 f \n'
    for offset in offsets:
        out += f'{offset:010d} 00000 n \n'.encode()
    out += b'trailer\n<< /Size ' + str(len(objects) + 1).encode() + b' /Root 1 0 R >>\nstartxref\n'
    out += str(xref).encode() + b'\n%%EOF\n'
    return bytes(out)


def _png(label):
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
    width = height = 64
    raw = b''.join(b'\x00' + b'\xdd\xdd\xdd' * width for _ in range(height))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'tEXt', b'Comment\x00Placeholder ' + label.encode('latin-1', 'replace'))
            + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def _zip(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries:
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return buffer.getvalue()


def _escape_xml(text):
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _docx(label):
    text = _escape_xml('Placeholder - scrambled test copy - ' + label)
    return _zip([
        ('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'),
        ('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'),
        ('word/document.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>' + text + '</w:t></w:r></w:p></w:body></w:document>')])


def _xlsx(label):
    text = _escape_xml('Placeholder - scrambled test copy - ' + label)
    return _zip([
        ('[Content_Types].xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>'),
        ('_rels/.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>'),
        ('xl/workbook.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>'),
        ('xl/_rels/workbook.xml.rels', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'),
        ('xl/worksheets/sheet1.xml', '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>' + text + '</t></is></c></row></sheetData></worksheet>')])


WEBP = base64.b64decode('UklGRhoAAABXRUJQVlA4TA0AAAAvAAAAEAcQERGIiP4HAA==')
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tif', '.tiff', '.heic', '.heif'}


def placeholder(extension, label):
    """Bytes of a harmless file of the same type; `label` makes each one unique."""
    extension = (extension or '').lower()
    if extension == '.pdf':
        return _pdf(label)
    if extension in IMAGE_EXTENSIONS:
        return _png(label)
    if extension == '.docx':
        return _docx(label)
    if extension == '.xlsx':
        return _xlsx(label)
    return ('Placeholder - scrambled test copy - ' + label + '\n').encode()


def scrambled_filename(scrambler, original, prefix='file'):
    suffix = Path(original).suffix.lower()
    if len(suffix) > 6 or not re.fullmatch(r'\.[a-z0-9]+', suffix or '.x'):
        suffix = ''
    return f'{prefix}-{scrambler.digest(original)[:16]}{suffix}'


# ------------------------------------------------------- Drive (decomposedfs)
def unpack(data):
    """Minimal msgpack reader for oCIS node metadata: one map of str -> bin/str."""
    position = 0

    def take(count):
        nonlocal position
        piece = data[position:position + count]
        if len(piece) != count:
            raise ValueError('Truncated metadata')
        position += count
        return piece

    def item():
        marker = take(1)[0]
        if 0xa0 <= marker <= 0xbf:
            return take(marker & 0x1f).decode()
        if marker in (0xd9, 0xda, 0xdb):
            size = int.from_bytes(take({0xd9: 1, 0xda: 2, 0xdb: 4}[marker]), 'big')
            return take(size).decode()
        if marker in (0xc4, 0xc5, 0xc6):
            size = int.from_bytes(take({0xc4: 1, 0xc5: 2, 0xc6: 4}[marker]), 'big')
            return take(size)
        raise ValueError('Unsupported metadata encoding')
    marker = take(1)[0]
    if 0x80 <= marker <= 0x8f:
        count = marker & 0x0f
    elif marker == 0xde:
        count = int.from_bytes(take(2), 'big')
    elif marker == 0xdf:
        count = int.from_bytes(take(4), 'big')
    else:
        raise ValueError('Metadata is not a map')
    result = {}
    for _ in range(count):
        key = item()
        result[key] = item()
    return result


def pack(mapping):
    def string(text):
        raw = text.encode()
        if len(raw) < 32:
            return bytes([0xa0 | len(raw)]) + raw
        if len(raw) < 256:
            return b'\xd9' + bytes([len(raw)]) + raw
        return b'\xda' + len(raw).to_bytes(2, 'big') + raw

    def binary(raw):
        if isinstance(raw, str):
            raw = raw.encode()
        if len(raw) < 256:
            return b'\xc4' + bytes([len(raw)]) + raw
        if len(raw) < 65536:
            return b'\xc5' + len(raw).to_bytes(2, 'big') + raw
        return b'\xc6' + len(raw).to_bytes(4, 'big') + raw
    count = len(mapping)
    out = bytearray(bytes([0x80 | count]) if count < 16 else b'\xde' + count.to_bytes(2, 'big'))
    for key, value in mapping.items():
        out += string(key) + binary(value)
    return bytes(out)


def split_id(identifier):
    if not re.fullmatch(r'[0-9a-f]{8}-[0-9a-f-]+', identifier):
        raise ValueError('Unexpected node identifier')
    return Path(identifier[0:2], identifier[2:4], identifier[4:6], identifier[6:8], identifier[8:])


def _when(value):
    text = value.decode() if isinstance(value, bytes) else str(value)
    return datetime.fromisoformat(text[:19]).replace(tzinfo=timezone.utc)


def remove(path):
    path = Path(path)
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def cripple_drive(root, cutoff, scrambler):
    """Rewrite a copied oCIS data directory in place (never production's own)."""
    root = Path(root)
    report = {'kept_files': 0, 'removed_files': 0, 'renamed_folders': 0}
    for name in ['search', 'thumbnails', 'nats']:
        remove(root / name)
    uploads = root / 'storage/users/uploads'
    if uploads.is_dir():
        for item in uploads.iterdir():
            remove(item)
    for space in sorted((root / 'storage/users/spaces').glob('*/*')):
        nodes, blobs = space / 'nodes', space / 'blobs'
        for item in (space / 'trash').glob('*') if (space / 'trash').is_dir() else []:
            remove(item)
        # Node files are named by ID; user file names exist only as symlinks.
        for revision in [p for p in nodes.rglob('*') if not p.is_symlink() and ('.REV.' in p.name or '.T.' in p.name)]:
            remove(revision)
        metadata = {}
        for file in [f for f in nodes.rglob('*.mpk') if not f.is_symlink()]:
            metadata[Path(str(file)[:-4])] = unpack(file.read_bytes())
        referenced = set()
        for base, values in metadata.items():
            kind = values.get('user.ocis.type', b'')
            kind = kind.decode() if isinstance(kind, bytes) else str(kind)
            name = values.get('user.ocis.name', b'')
            name = name.decode() if isinstance(name, bytes) else str(name)
            parent = values.get('user.ocis.parentid')
            parent_dir = nodes / split_id(parent.decode() if isinstance(parent, bytes) else parent) if parent else None
            for key in [key for key in values if key.startswith(('user.ocis.tags', 'user.ocis.md.'))
                        or key == 'user.ocis.space.description']:
                del values[key]
            if 'user.ocis.space.name' in values and values.get('user.ocis.space.alias', b'').startswith(b'personal/'):
                values['user.ocis.space.name'] = scrambler.value('person', values['user.ocis.space.name']).encode()
            if kind == '1':
                when = values.get('user.ocis.mtime')
                if when is not None and _when(when) < cutoff:
                    for path in [Path(str(base) + '.mpk'), Path(str(base) + '.mlock'), base]:
                        remove(path)
                    if parent_dir is not None and name:
                        remove(parent_dir / name)
                    report['removed_files'] += 1
                    continue
                identifier = values.get('user.ocis.id', base.name.encode())
                identifier = identifier.decode() if isinstance(identifier, bytes) else identifier
                data = placeholder(Path(name).suffix, identifier)
                blobid = values.get('user.ocis.blobid', b'').decode()
                if blobid:
                    target = blobs / split_id(blobid)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    referenced.add(target)
                values['user.ocis.blobsize'] = str(len(data)).encode()
                values['user.ocis.cs.md5'] = hashlib.md5(data).digest()
                values['user.ocis.cs.sha1'] = hashlib.sha1(data).digest()
                values['user.ocis.cs.adler32'] = struct.pack('>I', zlib.adler32(data) & 0xffffffff)
                for key in [key for key in values if key.startswith('user.ocis.cs.')
                            and key not in {'user.ocis.cs.md5', 'user.ocis.cs.sha1', 'user.ocis.cs.adler32'}]:
                    del values[key]
                new_name = scrambled_filename(scrambler, name)
                report['kept_files'] += 1
            elif kind == '2' and parent is not None and name:
                new_name = 'Folder ' + scrambler.digest(name)[:8]
                report['renamed_folders'] += 1
            else:
                new_name = name
            if new_name != name and parent_dir is not None:
                link = parent_dir / name
                if link.is_symlink():
                    link.rename(parent_dir / new_name)
                values['user.ocis.name'] = new_name.encode()
            Path(str(base) + '.mpk').write_bytes(pack(values))
        if blobs.is_dir():
            for blob in [p for p in blobs.rglob('*') if p.is_file() or p.is_symlink()]:
                if blob not in referenced:
                    blob.unlink()
    return report


# --------------------------------------------------------- database helpers
def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def _start(image, environment, ready):
    name = 'cripple-' + uuid.uuid4().hex[:12]
    args = ['docker', 'run', '-d', '--name', name, '--network', 'none']
    for key, value in environment.items():
        args += ['-e', f'{key}={value}']
    run(args + [image], stdout=subprocess.DEVNULL)
    for _ in range(180):
        if subprocess.run(['docker', 'exec', name, 'sh', '-c', ready], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode == 0:
            # Official images restart once after initialisation; settle.
            time.sleep(3)
            if subprocess.run(['docker', 'exec', name, 'sh', '-c', ready], stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL).returncode == 0:
                return name
        time.sleep(1)
    subprocess.run(['docker', 'rm', '-f', '-v', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raise RuntimeError('Temporary database did not start')


MYSQL = 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb -uroot "$@"'
PSQL = 'export PGPASSWORD="$POSTGRES_PASSWORD"; exec psql -v ON_ERROR_STOP=1 -At -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$@"'


def _feed(args, path=None, text=None):
    process = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        if path is not None:
            with open(path, 'rb') as stream:
                shutil.copyfileobj(stream, process.stdin)
        else:
            process.stdin.write(text.encode())
        process.stdin.close()
    except BrokenPipeError:
        pass  # the client stopped early; its own error message follows
    errors = process.stderr.read()
    if process.wait():
        raise RuntimeError('Temporary database command failed: ' + errors.decode(errors='replace')[-600:])


def mysql_rows(container, database, query):
    output = subprocess.check_output(['docker', 'exec', container, 'sh', '-c', MYSQL, 'sh', '-N', '-B', database,
                                      '-e', query], text=True)
    return [line.split('\t') for line in output.splitlines()]


def psql_rows(container, query):
    output = subprocess.check_output(['docker', 'exec', container, 'sh', '-c', PSQL, 'sh', '-F', '\t', '-c', query],
                                     text=True)
    return [line.split('\t') for line in output.splitlines() if line]


def _dump(args, path):
    with open(path, 'wb') as output:
        process = subprocess.run(args, stdout=output, stderr=subprocess.PIPE)
    if process.returncode:
        raise RuntimeError('Temporary database dump failed')


def read_erp_meta(container, database):
    doctypes = {row[0]: {'istable': row[1] == '1', 'issingle': row[2] == '1', 'is_submittable': row[3] == '1'}
                for row in mysql_rows(container, database,
                                      'SELECT name, istable, issingle, is_submittable FROM tabDocType')}
    fields = [tuple(row) for row in mysql_rows(container, database,
              "SELECT parent, fieldname, fieldtype, IFNULL(options,'') FROM tabDocField")]
    fields += [tuple(row) for row in mysql_rows(container, database,
               "SELECT dt, fieldname, fieldtype, IFNULL(options,'') FROM `tabCustom Field`")]
    columns = {}
    for table_name, column in mysql_rows(container, database, 'SELECT TABLE_NAME, COLUMN_NAME FROM '
                                         f'information_schema.COLUMNS WHERE TABLE_SCHEMA={sql_literal(database)}'):
        columns.setdefault(table_name, set()).add(column)
    # Columns in a unique index need collision-proof fakes (the name pools are small).
    unique = {(row[0], row[1]) for row in mysql_rows(container, database,
              'SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA='
              f"{sql_literal(database)} AND NON_UNIQUE=0 AND INDEX_NAME<>'PRIMARY'")}
    types = {(row[0], row[1]): row[2] for row in mysql_rows(container, database,
             'SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='
             f'{sql_literal(database)}')}
    return {'doctypes': doctypes, 'fields': [f for f in fields if len(f) == 4], 'columns': columns,
            'unique': unique, 'types': types}


def check_parity(container, database, scrambler):
    """The SQL fakes must equal the Python fakes for the same key."""
    samples = ['ravi@example.com', 'Example Traders', '+91 99999 00000']
    for kind in SPEC:
        for sample in samples:
            expression = mariadb_expression(kind, sql_literal(sample)).replace('@ck', sql_literal(scrambler.key))
            got = mysql_rows(container, database, f'SELECT {expression}')[0][0]
            if got != scrambler.value(kind, sample):
                raise RuntimeError('SQL and Python scrambling disagree for ' + kind)


# ---------------------------------------------------------------------- DMS
def dms_statements(rows, scrambler, keep_accounts, placeholders):
    """Python-computed statements for the remaining DMS rows (small tables).
    `rows` holds documents, correspondents, tags and users read from the copy."""
    keep = {account.casefold() for account in keep_accounts}
    out = []
    for doc_id, mime, original, filename, archive in rows['documents']:
        extension = Path(filename or original).suffix.lower() or {
            'application/pdf': '.pdf', 'image/png': '.png', 'image/jpeg': '.jpg'}.get(mime, '')
        label = 'document ' + doc_id
        content = placeholder(extension, label)
        new_filename = f'{int(doc_id):07d}{extension}'
        placeholders[('documents/originals', new_filename)] = content
        values = {'title': f'Document {scrambler.digest("doc|" + doc_id)[:8]}', 'content': PLACEHOLDER_TEXT,
                  'original_filename': scrambled_filename(scrambler, original or filename or doc_id),
                  'filename': new_filename, 'checksum': hashlib.md5(content).hexdigest()}
        if archive:
            archived = placeholder('.pdf', label + ' (archive)')
            values['archive_filename'] = f'{int(doc_id):07d}.pdf'
            values['archive_checksum'] = hashlib.md5(archived).hexdigest()
            placeholders[('documents/archive', values['archive_filename'])] = archived
        placeholders[('documents/thumbnails', f'{int(doc_id):07d}.webp')] = WEBP
        # Two phases avoid transient clashes on unique filename/checksum columns.
        out.append(f"UPDATE documents_document SET filename='tmp-{int(doc_id)}', checksum='tmp-{int(doc_id)}'"
                   + (f", archive_filename='tmp-{int(doc_id)}', archive_checksum='tmp-{int(doc_id)}'" if archive else '')
                   + f' WHERE id={int(doc_id)}')
        out.append('UPDATE documents_document SET ' + ', '.join(f'{k}={sql_literal(v)}' for k, v in values.items())
                   + f' WHERE id={int(doc_id)}')
    for row_id, name in rows['correspondents']:
        out.append(f"UPDATE documents_correspondent SET name={sql_literal('Correspondent ' + scrambler.digest('corr|' + name)[:8])}, "
                   f"match='' WHERE id={int(row_id)}")
    for row_id, name in rows['tags']:
        out.append(f"UPDATE documents_tag SET name={sql_literal('Tag ' + scrambler.digest('tag|' + name)[:8])}, "
                   f"match='' WHERE id={int(row_id)}")
    for row_id, username, email in rows['users']:
        if username.casefold() in keep or (email and email.casefold() in keep):
            continue
        # Linked SSO identities and e-mail addresses carry the real login.
        out.append(f'DELETE FROM socialaccount_socialaccount WHERE user_id={int(row_id)}')
        out.append(f'DELETE FROM account_emailaddress WHERE user_id={int(row_id)}')
        person = scrambler.value('person', username).split(' ')
        out.append('UPDATE auth_user SET '
                   f"username={sql_literal('user-' + scrambler.digest(username)[:10])}, "
                   f"email={sql_literal(scrambler.value('email', email) if email else '')}, "
                   f"first_name={sql_literal(person[0])}, last_name={sql_literal(person[-1])}, "
                   f"password='!' WHERE id={int(row_id)}")
    return out


def cripple_dms(container, data, cutoff, scrambler, keep_accounts):
    exists = lambda table_name: psql_rows(container, f"SELECT to_regclass('public.{table_name}') IS NOT NULL")[0][0] == 't'
    cut = sql_literal(cutoff.strftime('%Y-%m-%d %H:%M:%S+00'))
    statements = ['SET session_replication_role = replica']
    for table_name in ['auditlog_logentry', 'django_admin_log', 'documents_paperlesstask', 'documents_sharelink',
                       'paperless_mail_processedmail', 'documents_workflowrun', 'django_session',
                       'authtoken_token', 'socialaccount_socialtoken']:
        if exists(table_name):
            statements.append(f'DELETE FROM {table_name}')
    soft = psql_rows(container, "SELECT count(*) FROM information_schema.columns WHERE table_name='documents_document' "
                                "AND column_name='deleted_at'")[0][0] != '0'
    statements.append(f'DELETE FROM documents_document WHERE added < {cut}' + (' OR deleted_at IS NOT NULL' if soft else ''))
    if exists('documents_note'):
        statements.append(f"UPDATE documents_note SET note={sql_literal(PLACEHOLDER_TEXT)}")
    if exists('documents_customfieldinstance'):
        for column in ['value_text', 'value_url', 'value_select', 'value_document_ids']:
            if psql_rows(container, "SELECT count(*) FROM information_schema.columns WHERE "
                         f"table_name='documents_customfieldinstance' AND column_name='{column}'")[0][0] != '0':
                statements.append(f'UPDATE documents_customfieldinstance SET {column}=NULL')
    if exists('paperless_mail_mailaccount'):
        statements.append("UPDATE paperless_mail_mailaccount SET username='test', password='', "
                          "imap_server='mail.example.invalid'")
    _feed(['docker', 'exec', '-i', container, 'sh', '-c', PSQL, 'sh'], text=';\n'.join(statements) + ';\n')
    # Remove rows left pointing at deleted documents (Django keeps FKs without cascade).
    foreign = psql_rows(container, "SELECT c.conrelid::regclass::text, a.attname, c.confrelid::regclass::text, "
                        "fa.attname FROM pg_constraint c JOIN pg_attribute a ON a.attrelid=c.conrelid AND "
                        "a.attnum=c.conkey[1] JOIN pg_attribute fa ON fa.attrelid=c.confrelid AND fa.attnum=c.confkey[1] "
                        "WHERE c.contype='f' AND array_length(c.conkey,1)=1")
    cleanup = ['SET session_replication_role = replica']
    for _ in range(3):
        for child, column, parent, parent_column in foreign:
            cleanup.append(f'DELETE FROM {child} c WHERE c.{column} IS NOT NULL AND NOT EXISTS '
                           f'(SELECT 1 FROM {parent} p WHERE p.{parent_column}=c.{column})')
    _feed(['docker', 'exec', '-i', container, 'sh', '-c', PSQL, 'sh'], text=';\n'.join(cleanup) + ';\n')
    rows = {'documents': psql_rows(container, "SELECT id, coalesce(mime_type,''), coalesce(original_filename,''), "
                                   "coalesce(filename,''), coalesce(archive_filename,'') FROM documents_document"),
            'correspondents': psql_rows(container, 'SELECT id, name FROM documents_correspondent'),
            'tags': psql_rows(container, 'SELECT id, name FROM documents_tag') if exists('documents_tag') else [],
            'users': psql_rows(container, "SELECT id, username, coalesce(email,'') FROM auth_user")}
    placeholders = {}
    updates = dms_statements(rows, scrambler, keep_accounts, placeholders)
    if updates:
        _feed(['docker', 'exec', '-i', container, 'sh', '-c', PSQL, 'sh'],
              text='SET session_replication_role = replica;\n' + ';\n'.join(updates) + ';\n')
    media = data / 'dms-media'
    remove(media / 'documents')
    for (folder, name), content in placeholders.items():
        target = media / folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    for name in ['index', 'classification_model.pickle']:
        remove(data / 'dms-data' / name)
    consume = data / 'dms-consume'
    if consume.is_dir():
        for item in consume.iterdir():
            remove(item)
    return {'documents': len(rows['documents'])}


# ---------------------------------------------------------------- orchestration
def cripple(data, config, containers, database, counts_function, audit=None):
    """Transform the snapshot staging directory `data` in place.

    Production is already running again: this works only on copies. Returns
    the manifest record, including business counts read from the crippled copies.
    """
    settings = config.get('cripple') or {}
    days = int(settings.get('days', 60))
    if days < 1 or days > 3650:
        raise ValueError('Invalid cripple window')
    keep = [str(account) for account in settings.get('keep_accounts', [])]
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    scrambler = Scrambler()
    data = Path(data)
    erp_image = json.loads(subprocess.check_output(['docker', 'inspect', containers['erp_database']]))[0]['Config']['Image']
    dms_image = json.loads(subprocess.check_output(['docker', 'inspect', containers['dms_database']]))[0]['Config']['Image']
    password = secrets.token_hex(16)
    started = []
    try:
        # TCP checks: the official images first initialise on a private socket.
        erp = _start(erp_image, {'MARIADB_ROOT_PASSWORD': password, 'MYSQL_ROOT_PASSWORD': password},
                     'mariadb-admin ping -h127.0.0.1 --protocol=tcp -uroot -p"$MYSQL_ROOT_PASSWORD" >/dev/null 2>&1')
        started.append(erp)
        dms = _start(dms_image, {'POSTGRES_PASSWORD': password, 'POSTGRES_USER': 'cripple', 'POSTGRES_DB': 'cripple'},
                     'pg_isready -h 127.0.0.1 -U cripple -d cripple')
        started.append(dms)
        _feed(['docker', 'exec', '-i', erp, 'sh', '-c', MYSQL, 'sh'],
              text=f'CREATE DATABASE {quote(database)} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\n')
        _feed(['docker', 'exec', '-i', erp, 'sh', '-c', MYSQL, 'sh', database], path=data / 'erp.sql')
        check_parity(erp, database, scrambler)
        plan = erp_plan(read_erp_meta(erp, database), cutoff, keep, scrambler.key)
        _feed(['docker', 'exec', '-i', erp, 'sh', '-c', MYSQL, 'sh', database], text=';\n'.join(plan) + ';\n')
        files = mysql_rows(erp, database, 'SELECT new, is_private FROM `_cripple_files`')
        _feed(['docker', 'exec', '-i', erp, 'sh', '-c', MYSQL, 'sh', database],
              text='DROP TABLE `_cripple_map`; DROP TABLE `_cripple_files`;\n')
        remove(data / 'erp-files')
        for url, private in files:
            folder = data / 'erp-files' / ('private' if private == '1' else 'public')
            target = folder / url.split('/files/', 1)[1]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(placeholder(Path(url).suffix, Path(url).name))
        _feed(['docker', 'exec', '-i', dms, 'sh', '-c', PSQL, 'sh'], path=data / 'dms.sql')
        dms_report = cripple_dms(dms, data, cutoff, scrambler, keep)
        counts = counts_function({'erp_database': erp, 'dms_database': dms}, database)
        if audit is not None:
            audit(erp, database)
        _dump(['docker', 'exec', erp, 'sh', '-c', 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mariadb-dump -uroot '
               '--single-transaction --routines --triggers --hex-blob "$1"', 'sh', database], data / 'erp.sql')
        _dump(['docker', 'exec', dms, 'sh', '-c', 'export PGPASSWORD="$POSTGRES_PASSWORD"; exec pg_dump -U '
               '"$POSTGRES_USER" --no-owner --no-acl "$POSTGRES_DB"'], data / 'dms.sql')
    finally:
        for name in started:
            subprocess.run(['docker', 'rm', '-f', '-v', name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    drive_report = cripple_drive(data / 'drive-data', cutoff, scrambler) if (data / 'drive-data').is_dir() else {}
    for name in ['mail-data', 'document-jobs.sqlite3']:
        remove(data / name)
    enrollment = data / 'document-enrollment.json'
    if enrollment.exists():
        value = json.loads(enrollment.read_text())
        value['users'] = [user for user in value.get('users', []) if user.get('email', '').casefold()
                          in {account.casefold() for account in keep}]
        enrollment.write_text(json.dumps(value) + '\n')
    return {'policy': POLICY, 'days': days, 'cutoff': cutoff.isoformat(), 'kept_accounts': len(keep),
            'erp_files': len(files), 'dms': dms_report, 'drive': drive_report,
            'mail': 'not exported: test mailboxes start empty', 'counts': counts}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Print the field classification for a fieldname (diagnostic).')
    parser.add_argument('fieldname')
    parser.add_argument('--fieldtype', default='Data')
    args = parser.parse_args()
    print(category(args.fieldname, args.fieldtype))
