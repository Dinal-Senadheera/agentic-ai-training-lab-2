---
doc_id: install-classic-v3
title: Installing Aralia POS Classic (3.x)
type: manual
product_version: classic-3.x
updated: 2025-08-14
visibility: internal
tenant: none
---

# Installing Aralia POS Classic (3.x)

Aralia POS Classic is the on-premise edition. Each till runs a local database and a
background **Sync Agent** that uploads sales to head office.

## Requirements
- Windows 10 or Windows 11 (64-bit). Classic does not run on macOS or Linux.
- Microsoft SQL Server Express 2019 or later on the till.
- 4 GB RAM minimum, 8 GB recommended.

## Network
The Sync Agent connects outbound to sync.aralia.example on **TCP port 7341**. Open this
port on the store firewall. No inbound ports are required. If port 7341 is blocked the
Sync Agent keeps sales locally and retries (see Offline mode for Classic).

## Installation steps
1. Run AraliaClassicSetup.exe as administrator.
2. Enter the store licence key printed on the welcome letter.
3. Choose the till number (01 to 16).
4. Restart the till when prompted. The Sync Agent starts automatically.


---
Need help? Aralia Support is available 24/7 on +94 11 000 0000 or support@aralia.example. Aralia Systems (Pvt) Ltd, Colombo 03, Sri Lanka. Product names and specifications may change without notice. Always check the latest release notes before advising merchants.
