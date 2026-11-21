---
doc_id: api-rate-limits
title: API rate limits
type: reference
product_version: cloud-4.x
updated: 2026-07-01
visibility: internal
tenant: none
---

# API rate limits

Merchant integrations (e-commerce sync, accounting exports) call the Aralia public API.

- Each merchant has a **daily API call allowance** set by their plan. The allowance for
  each plan is in the Plans and limits sheet. Some merchants have a different allowance
  in their contract addendum; the addendum always takes precedence.
- Daily counters reset at **00:00 Asia/Colombo time**.
- A burst limit of 20 requests per second applies to every plan.
- When the daily allowance is used up, the API returns HTTP 429 and the till shows E-3301.


---
Need help? Aralia Support is available 24/7 on +94 11 000 0000 or support@aralia.example. Aralia Systems (Pvt) Ltd, Colombo 03, Sri Lanka. Product names and specifications may change without notice. Always check the latest release notes before advising merchants.
