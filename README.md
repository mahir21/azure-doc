# Bulk Date Extractor MVP

An AI-powered web app that extracts important dates from scanned documents and exports selected results as calendar events.

This MVP is designed for admin-heavy workflows where users need to process many scanned PDFs, detect hearings, appointments, summons dates, and deadlines, then export them to a calendar file.

# 2. In your project folder terminal
Run:
------------------------------------
git init
git add .
git commit -m "Initial MVP for bulk date extractor"

---------------------------------------

## Then connect to GitHub:

git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/bulk-date-extractor-mvp.git
git push -u origin main

-----------------------------------------------------------------

# Add .gitignore
Create a file named:
.gitignore

### Put this inside:
__pycache__/
*.pyc
.env
.venv/
venv/
.DS_Store
.idea/

# 4. IMPORTANT: never upload Azure key
Do not put this in GitHub:
AZURE_DI_KEY="..."

# 5. Your repo should look like this
bulk-date-extractor-mvp/
  main.py
  requirements.txt
  README.md
  .gitignore

  
