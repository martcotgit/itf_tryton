
import os
import sys
import django
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itf_portal.settings.base')
django.setup()

from apps.accounts.services import PortalOrderService

def debug_orders():
    login = "martcot@gmail.com"
    print(f"Debugging orders for {login}...")
    
    service = PortalOrderService()
    
    # 1. List all orders to see their raw states
    print("\n--- Listing Orders ---")
    try:
        result = service.list_orders(login=login, page_size=100)
        if not result.orders:
            print("No orders found via list_orders!")
        else:
            for order in result.orders:
                print(f"Order {order.number} (Ref: {order.reference}): State='{order.state}', Total={order.total_amount}")
    except Exception as e:
        print(f"Error listing orders: {e}")

    # 2. Check specific counts
    print("\n--- Checking Counts ---")
    statuses_to_check = ["draft", "quotation", "confirmed", "processing", "sent", "done", "cancelled"]
    for status in statuses_to_check:
        try:
            # using list_orders to count as _count_orders is a private method in view
            result = service.list_orders(login=login, statuses=[status], page_size=1)
            count = result.pagination.total
            print(f"Count for ['{status}']: {count}")
        except Exception as e:
            print(f"Error counting '{status}': {e}")

if __name__ == "__main__":
    debug_orders()
