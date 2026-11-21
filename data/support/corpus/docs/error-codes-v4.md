---
doc_id: error-codes-v4
title: Error code reference for Aralia POS Cloud
type: reference
product_version: cloud-4.x
updated: 2026-09-15
visibility: internal
tenant: none
---

# Error code reference for Aralia POS Cloud

| Code | Meaning | What to do |
|---|---|---|
| E-1024 | Card reader timeout | Reseat the card reader's USB cable and retry the payment. |
| E-1042 | Device offline: a cloud printer or KDS lost its MQTT connection | Check that outbound port 8883 is open, then restart the device. |
| E-1402 | Barcode scanner not paired | Re-pair the scanner in Settings > Devices > Scanners. |
| E-2207 | Sync token expired | Sign out and sign in again with the merchant admin account. Tokens are valid for 30 days. |
| E-2270 | Clock skew detected | The device clock differs from server time by more than 5 minutes. Turn on automatic date and time. |
| E-3301 | API daily limit exceeded (HTTP 429) | The limit resets at 00:00 Asia/Colombo time. Upgrade the plan or contact sales for a higher limit. |
| E-4100 | Loyalty points expired | Explain the expiry rule to the customer. Points cannot be restored. |


---
Need help? Aralia Support is available 24/7 on +94 11 000 0000 or support@aralia.example. Aralia Systems (Pvt) Ltd, Colombo 03, Sri Lanka. Product names and specifications may change without notice. Always check the latest release notes before advising merchants.
