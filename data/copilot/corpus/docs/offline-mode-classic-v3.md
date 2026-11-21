---
doc_id: offline-mode-classic-v3
title: Offline mode in Aralia POS Classic (3.x)
type: manual
product_version: classic-3.x
updated: 2025-08-14
visibility: internal
tenant: none
---

# Offline mode in Aralia POS Classic (3.x)

When the Sync Agent cannot reach head office, the till keeps trading offline.

- The till stores up to **500 transactions** locally. After 500 unsynced transactions,
  the till stops accepting new sales until it syncs.
- The Sync Agent retries the connection every **15 minutes**.
- **Card payments are disabled** while offline. Cash and gift vouchers still work.
- When the connection returns, transactions upload oldest first.


---
Need help? Aralia Support is available 24/7 on +94 11 000 0000 or support@aralia.example. Aralia Systems (Pvt) Ltd, Colombo 03, Sri Lanka. Product names and specifications may change without notice. Always check the latest release notes before advising merchants.
