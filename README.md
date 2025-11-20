# काव्य संग्रह — Poem Website

A lightweight Flask + SQLite website to showcase a collection of poems with background images, subscribers, likes/dislikes, comments, writer details, and view counters.

## Features
- Add new poem (title, content, date, background image upload or URL)
- Writer details card on the homepage
- Subscribe by email (cookie-based access for reactions/comments)
- Like/Dislike per poem (one reaction per subscriber)
- Commenting for subscribers
- Poem view count
- Lightweight UI inspired by the screenshot

## Quickstart (Windows PowerShell)
```powershell
# From the repository root
cd "c:\Users\harsh\OneDrive\Desktop\personal\poem"

# Optional: create and activate a virtual environment
py -m venv .venv; .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Set admin password for adding poems (change it!)
$env:ADMIN_PASSWORD = "your-strong-password"

# Initialize database and seed writer
$env:FLASK_APP="app.py"; python .\app.py
# In a separate terminal the first time only (or visit http://127.0.0.1:5000/init-db)
python -c "import requests; print(requests.get('http://127.0.0.1:5000/init-db').text)" 2>$null

# Run the app (if not already running)
python .\app.py
```
Open http://127.0.0.1:5000 in your browser.

## Usage
- Add poem: “नई कविता जोड़ें” in the top nav.
- Subscribe: “सदस्य बनें” → enter email. A cookie unlocks like/comment features.
- Add poem: Admins visit `/admin/login` then use “नई कविता जोड़ें”. Logout via “लॉगआउट”.
- Like/Dislike: buttons on a poem page; updates your reaction.
- Comments: available to subscribers on poem pages.

## Deploying
- App is file-backed SQLite; copy the folder to a lightweight host (Render, Railway, Azure Web Apps, etc.).
- Set environment variable `SECRET_KEY` in production.
- For static hosting only, you can export static pages later, but dynamic features (comments/likes) require a Python server.

## Notes
- This project avoids heavy dependencies; uses only Flask and SQLAlchemy.
- Image uploads are saved under `static/images/`. Ensure the host allows writing to this folder.
