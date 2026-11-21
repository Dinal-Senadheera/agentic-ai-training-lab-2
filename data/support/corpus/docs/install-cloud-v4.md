---
doc_id: install-cloud-v4
title: Setting up a store on Aralia POS Cloud (4.x)
type: manual
product_version: cloud-4.x
updated: 2026-06-02
visibility: internal
tenant: none
attachments: img-store-network
---

# Setting up a store on Aralia POS Cloud (4.x)

Aralia POS Cloud runs in the browser or on Sunmi all-in-one devices. There is no local
database and no Sync Agent.

## Network requirements
- Outbound **HTTPS on port 443** to api.aralia.example for all till traffic.
- Outbound **MQTT over TLS on port 8883** to devices.aralia.example. Cloud printers and
  kitchen display screens (KDS) use this connection. If 8883 is blocked, printers and
  KDS go offline even though the till itself still works.
- No inbound ports are required.
- Minimum 2 Mbps stable bandwidth per store.

## Store network layout
Use the standard store network layout shown in the attached diagram (img-store-network).
POS devices, printers and KDS screens sit on their own VLAN, separate from guest Wi-Fi.
Printers and KDS screens use fixed IP addresses so that the cloud can find them; the
addresses are listed on the diagram.

## Supported browsers
Chrome 120 or later and Edge 120 or later.


---
Need help? Aralia Support is available 24/7 on +94 11 000 0000 or support@aralia.example. Aralia Systems (Pvt) Ltd, Colombo 03, Sri Lanka. Product names and specifications may change without notice. Always check the latest release notes before advising merchants.
