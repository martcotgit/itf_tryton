
import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itf_portal.settings.base')
django.setup()

from apps.accounts.services import PortalInvoiceService, PortalAccountService

def debug_invoices():
    login = "martcot@gmail.com"
    print(f"Debugging invoices for {login}...")
    
    service = PortalInvoiceService()
    
    # 1. List all invoices to see their raw states
    print("\n--- Listing Invoices ---")
    try:
        result = service.list_invoices(login=login, page_size=100)
        if not result.invoices:
            print("No invoices found via list_invoices!")
        else:
            for inv in result.invoices:
                print(f"Invoice {inv.number}: State='{inv.state}', Amount={inv.total_amount}, Due={inv.amount_due}")
    except Exception as e:
        print(f"Error listing invoices: {e}")

    # 2. Check specific counts
    print("\n--- Checking Counts ---")
    statuses_to_check = ["posted", "validated", "waiting_payment", "draft", "paid"]
    for status in statuses_to_check:
        try:
            count = service.count_invoices(login=login, statuses=[status])
            print(f"Count for ['{status}']: {count}")
        except Exception as e:
            print(f"Error counting '{status}': {e}")

if __name__ == "__main__":
    debug_invoices()
