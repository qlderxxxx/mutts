# Supabase Setup Guide - Step by Step

## 📋 Quick Setup Checklist

Follow these steps to set up your Supabase database:

### Step 1: Create a Supabase Account

1. Go to **https://supabase.com**
2. Click **"Start your project"** or **"Sign In"** (top right)
3. Sign up using:
   - GitHub account (recommended - fastest)
   - Email and password
   - Or other OAuth providers

### Step 2: Create a New Project

1. Once logged in, you'll see the Supabase dashboard
2. Click **"New Project"** (green button)
3. Fill in the project details:
   - **Name**: `greyhound-micro-field` (or any name you prefer)
   - **Database Password**: Create a strong password (save this!)
   - **Region**: Choose closest to you (e.g., `Sydney` for Australia)
   - **Pricing Plan**: Select **"Free"** tier
4. Click **"Create new project"**
5. Wait 1-2 minutes for the project to initialize

### Step 3: Run the Database Schema

1. In your project dashboard, look at the left sidebar
2. Click on **"SQL Editor"** (icon looks like `</>`)
3. Click **"New query"** button
4. You'll see a blank SQL editor
5. **Copy the entire contents** of your `schema.sql` file
6. **Paste** it into the SQL editor
7. Click **"Run"** button (bottom right) or press `Ctrl+Enter`
8. You should see a success message: "Success. No rows returned"

### Step 4: Verify Tables Were Created

1. In the left sidebar, click **"Table Editor"** (icon looks like a table grid)
2. You should see two tables:
   - ✅ `races`
   - ✅ `runners`
3. Click on each table to verify the columns are correct

### Step 5: Get Your API Credentials

1. In the left sidebar, click **"Settings"** (gear icon at bottom)
2. Click **"API"** in the settings menu
3. You'll see two important sections:

   **Project URL:**
   ```
   https://xxxxxxxxxxxxx.supabase.co
   ```
   Copy this entire URL

   **Project API keys:**
   - Find the **"anon public"** key (not the service_role key!)
   - Click the copy icon to copy it
   - It looks like: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` (very long)

4. Save both of these somewhere safe (you'll need them in the next steps)

---

## 🔧 What to Do With Your Credentials

### For the Frontend (`index.html`)

1. Open `index.html` in your editor
2. Find these lines (around line 157):
   ```javascript
   const SUPABASE_URL = 'YOUR_SUPABASE_URL';
   const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';
   ```
3. Replace with your actual values:
   ```javascript
   const SUPABASE_URL = 'https://xxxxxxxxxxxxx.supabase.co';
   const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';
   ```

### For GitHub Actions (Scraper)

1. Push your code to GitHub first
2. Go to your GitHub repository
3. Click **Settings** tab
4. In the left sidebar, click **Secrets and variables** → **Actions**
5. Click **"New repository secret"**
6. Add two secrets:

   **First Secret:**
   - Name: `SUPABASE_URL`
   - Value: `https://xxxxxxxxxxxxx.supabase.co`
   - Click "Add secret"

   **Second Secret:**
   - Name: `SUPABASE_KEY`
   - Value: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
   - Click "Add secret"

---

## 🧪 Testing Your Setup

### Test 1: Verify Database Access

1. In Supabase, go to **SQL Editor**
2. Run this test query:
   ```sql
   SELECT * FROM races LIMIT 10;
   ```
3. You should see "Success. No rows returned" (because there's no data yet)

### Test 2: Test Frontend Connection (Optional)

1. Open `index.html` in a browser (after adding your credentials)
2. Open browser console (F12)
3. You should see "No micro-fields found" message (not an error)
4. Check console for any connection errors

### Test 3: Test Scraper Locally (Optional)

```powershell
# Set environment variables (Windows PowerShell)
$env:SUPABASE_URL="https://xxxxxxxxxxxxx.supabase.co"
$env:SUPABASE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Install dependencies
pip install -r requirements.txt

# Run scraper
python scraper.py
```

---

## ⚠️ Common Issues

### "Permission denied" or "RLS policy violation"

**Solution**: The schema includes RLS policies for public read access. If you get permission errors:

1. Go to **Authentication** → **Policies** in Supabase
2. Make sure the policies are enabled for both tables
3. Or temporarily disable RLS (not recommended for production):
   ```sql
   ALTER TABLE races DISABLE ROW LEVEL SECURITY;
   ALTER TABLE runners DISABLE ROW LEVEL SECURITY;
   ```

### "Table already exists" error

**Solution**: If you need to re-run the schema:

1. First drop the existing tables:
   ```sql
   DROP TABLE IF EXISTS runners CASCADE;
   DROP TABLE IF EXISTS races CASCADE;
   ```
2. Then run the full `schema.sql` again

### Can't find the SQL Editor

**Solution**: Make sure you're in your project dashboard (not the organization overview). The project name should be visible at the top.

---

## 📊 Visual Guide to Supabase Dashboard

```
┌─────────────────────────────────────────┐
│  Supabase Dashboard                     │
├─────────────────────────────────────────┤
│                                         │
│  Left Sidebar:                          │
│  ├─ 📊 Home                             │
│  ├─ 📝 Table Editor    ← Verify tables  │
│  ├─ </> SQL Editor     ← Run schema.sql │
│  ├─ 🔐 Authentication                   │
│  ├─ 📦 Storage                          │
│  └─ ⚙️  Settings       ← Get API keys   │
│      └─ API                             │
│                                         │
└─────────────────────────────────────────┘
```

---

## ✅ Checklist

- [ ] Created Supabase account
- [ ] Created new project
- [ ] Ran `schema.sql` in SQL Editor
- [ ] Verified `races` and `runners` tables exist
- [ ] Copied Project URL
- [ ] Copied anon public API key
- [ ] Updated `index.html` with credentials
- [ ] (If using GitHub Actions) Added secrets to GitHub

---

## 🎯 Next Steps After Setup

Once your database is set up:

1. **Update the scraper selectors** in `scraper.py` to match the actual website HTML
2. **Push to GitHub** and configure GitHub Actions
3. **Enable GitHub Pages** to host your frontend
4. **Test the full workflow** by manually triggering the GitHub Action

Need help with any of these steps? Just ask!
