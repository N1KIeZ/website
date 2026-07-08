"""Remove admin key system from app.py"""
import re

with open('backend/app_clean.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove ADMIN_KEY line
content = content.replace("ADMIN_KEY = \"admin123\"\n", "")
content = content.replace("ADMIN_KEY = 'admin123'\n", "")

# Remove the entire admin guard section (from comment through the function)
content = re.sub(
    r'# ─── Admin guard.*?return True\n\s*\n',
    '',
    content,
    flags=re.DOTALL
)

# Remove Depends(verify_admin) from all endpoint signatures
content = content.replace(', admin: bool = Depends(verify_admin)', '')
content = content.replace(', admin = Depends(verify_admin)', '')

# Remove Header from FastAPI import if no longer used
content = content.replace('from fastapi import FastAPI, HTTPException, Depends, Header',
                           'from fastapi import FastAPI, HTTPException, Depends')

with open('backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Cleanup temp file
import os
os.remove('backend/app_clean.py')
os.remove('backend/clean_app.py')

print("Done - admin key removed")
