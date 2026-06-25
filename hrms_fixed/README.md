# HRMS (Flask + SQLite)

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt --break-system-packages --ignore-installed
   ```

2. Run:
   ```bash
   python app.py
   ```

3. Open:
   - http://localhost:8000

## Default Admin Login

- **Username:** `admin`
- **Password:** `1234`

## Notes / Fixes Included

- Dashboard missing variables + charts fixed.
- Profile photo path fixed (`/static/uploads/...`) and uploads are stored with unique filenames.
- Added missing pages/routes:
  - `Employee Profile` page
  - `Add Notification` page
  - `Mark as Read` notification route
- Settings page now supports POST save + password change + theme switch.

