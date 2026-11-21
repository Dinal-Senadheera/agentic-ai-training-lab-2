---
doc_id: kds-setup-v4
title: Kitchen display (KDS) setup
type: manual
product_version: cloud-4.x
updated: 2026-06-10
visibility: internal
tenant: none
---

# Kitchen display (KDS) setup

Kitchen display screens show orders to kitchen staff in restaurants.

1. Mount the screen and connect it to the POS VLAN.
2. Give the screen the fixed IP address from the standard store network layout.
3. In Aralia POS Cloud, open Settings > Devices > Kitchen displays and pair the screen
   with the six-digit code it shows.

KDS screens receive orders over the same MQTT connection as cloud printers. When the
connection drops, the screen shows a device offline error and orders queue on the till.


---
Need help? Aralia Support is available 24/7 on +94 11 000 0000 or support@aralia.example. Aralia Systems (Pvt) Ltd, Colombo 03, Sri Lanka. Product names and specifications may change without notice. Always check the latest release notes before advising merchants.
