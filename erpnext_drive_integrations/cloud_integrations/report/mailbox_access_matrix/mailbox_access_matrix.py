"""Read-only native user/account matrix; never creates accounts or grants access."""
import hashlib
import frappe

def execute(filters=None):
 if frappe.session.user!='Administrator' and not ({'System Manager','Suite Admin','Mailbox Administrator'} & set(frappe.get_roles())):
  raise frappe.PermissionError('Mailbox administration permission is required')
 users=frappe.get_all('User',filters={'enabled':1,'name':['not in',['Guest','Administrator']]},fields=['name','full_name'],order_by='full_name')
 accounts=frappe.get_all('JMAP Account',fields=['name','_name','is_readonly'],order_by='_name')
 settings={x.user:x for x in frappe.get_all('User Settings',fields=['name','user','username'])}
 links={(x.user,x.account) for x in frappe.get_all('User Account',fields=['user','account'])}
 columns=[{'fieldname':'user','label':'Login username','fieldtype':'Data','width':230},
  {'fieldname':'full_name','label':'Name','fieldtype':'Data','width':150},
  {'fieldname':'mail_login','label':'Mail-server login','fieldtype':'Data','width':230}]
 fields={a.name:'mailbox_'+hashlib.sha256(a.name.encode()).hexdigest()[:12] for a in accounts}
 for a in accounts:
  columns.append({'fieldname':fields[a.name],'label':a._name or a.name,'fieldtype':'Data','width':200})
 rows=[]
 for u in users:
  setting=settings.get(u.name)
  row={'user':u.name,'full_name':u.full_name,'mail_login':(setting.username or '') if setting else ''}
  for a in accounts:row[fields[a.name]]='Access' if (u.name,a.name) in links else 'No access'
  rows.append(row)
 message='Access means an existing native mailbox assignment. No assignment means no mailbox. Login names and mailbox addresses are independent. This report does not change permissions or create mailboxes.'
 return columns,rows,message
