"""Historical entry point: restore native Invitations; never hide it again."""
import re
from authentik.brands.models import Brand
brand = Brand.objects.get(domain="sso.example.com")
before = brand.branding_custom_css
after = re.sub(r'/\* cloud-invitation-navigation \*/[\s\S]*?\}\s*', '', before)
if after != before:
    brand.branding_custom_css = after
    brand.save(update_fields=["branding_custom_css"])
print("NATIVE_INVITATION_NAVIGATION_VISIBLE")
