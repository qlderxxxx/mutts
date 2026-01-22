# Greyhound Micro-Field Finder

A mobile web app that identifies and displays greyhound races with micro-fields (4-5 runners), helping punters find value betting opportunities.

## 🎯 Features

- **Real-time tracking** of 4 and 5 runner greyhound races
- **Automatic scraping** from The Greyhound Recorder every 15 minutes
- **Mobile-first design** with premium UI
- **Live countdown timers** for upcoming races
- **Color-coded cards**:
  - 🔴 Red for 4-runner micro-fields
  - 🟠 Orange for 5-runner opportunities
- **Fixed win odds** display for each runner

## 🏗️ Architecture

- **Database**: Supabase (PostgreSQL)
- **Backend**: Python scraper running on GitHub Actions
- **Frontend**: Static HTML/CSS/JS hosted on GitHub Pages
- **Automation**: GitHub Actions (15-minute intervals)

## 📋 Setup Instructions

### 1. Supabase Setup

1. Create a free account at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to the SQL Editor and run the contents of `schema.sql`
4. Navigate to Settings → API
5. Copy your:
   - Project URL (`SUPABASE_URL`)
   - `anon` public key (`SUPABASE_KEY`)

### 2. GitHub Repository Setup

1. Create a new GitHub repository
2. Push this code to your repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin YOUR_REPO_URL
   git push -u origin main
   ```

3. Add GitHub Secrets:
   - Go to Settings → Secrets and variables → Actions
   - Add two secrets:
     - `SUPABASE_URL`: Your Supabase project URL
     - `SUPABASE_KEY`: Your Supabase anon key

4. Enable GitHub Pages:
   - Go to Settings → Pages
   - Source: Deploy from a branch
   - Branch: `main` / `root`
   - Save

### 3. Configure Frontend

Edit `index.html` and replace the placeholders:

```javascript
const SUPABASE_URL = 'YOUR_SUPABASE_URL';
const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';
```

### 4. Test the Scraper Locally (Optional)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export SUPABASE_URL="your_url_here"
export SUPABASE_KEY="your_key_here"

# Run the scraper
python scraper.py
```

### 5. Trigger the First Scrape

- Go to Actions tab in your GitHub repository
- Select "Scrape Greyhound Races" workflow
- Click "Run workflow"
- Wait for it to complete

### 6. View Your App

Your app will be available at:
```
https://YOUR_USERNAME.github.io/YOUR_REPO_NAME/
```

## 🔧 How It Works

### Scraper Logic

1. **Fetches** the form guide from The Greyhound Recorder
2. **Navigates** to "Today" and "Tomorrow" sections
3. **Iterates** through each meeting and race
4. **Counts active runners**:
   - Excludes scratched dogs
   - Excludes reserves without confirmed runs
   - Only counts actual starters
5. **Extracts** fixed win odds for each runner
6. **Upserts** data to Supabase (updates existing, inserts new)

### Frontend Query

```sql
SELECT * FROM races 
WHERE active_runner_count IN (4, 5) 
  AND race_time > NOW() 
ORDER BY race_time ASC
```

## ⚠️ Important Notes

### Web Scraping Disclaimer

This scraper targets `thegreyhoundrecorder.com.au`. Please:
- Respect their `robots.txt`
- Don't overload their servers
- Be prepared to update selectors if the site structure changes

### Supabase Free Tier Limits

- 500 MB database space
- 2 GB bandwidth per month
- 50,000 monthly active users

This should be more than sufficient for this use case.

### HTML Selector Updates Required

⚠️ **IMPORTANT**: The `scraper.py` file contains placeholder CSS selectors. You'll need to:

1. Visit https://www.thegreyhoundrecorder.com.au/form-guides/
2. Inspect the HTML structure
3. Update the selectors in `scraper.py` to match the actual HTML:
   - Meeting containers
   - Race elements
   - Runner tables
   - Dog names, box numbers, odds
   - Scratched/reserve status indicators
   - Race times

Look for comments marked with `# TODO` in the scraper code.

## 📱 Mobile Optimization

The frontend is optimized for mobile devices with:
- Responsive grid layouts
- Touch-friendly card interactions
- Readable fonts and spacing
- Smooth animations and transitions

## 🔄 Data Updates

- **Scraper runs**: Every 15 minutes via GitHub Actions
- **Frontend refreshes**: Every 2 minutes automatically
- **Manual refresh**: Reload the page

## 🛠️ Customization

### Change Scraping Frequency

Edit `.github/workflows/scrape.yml`:

```yaml
schedule:
  - cron: '*/15 * * * *'  # Change to your preferred schedule
```

### Adjust Frontend Refresh Rate

Edit `index.html`:

```javascript
// Refresh data every 2 minutes (change as needed)
setInterval(loadRaces, 2 * 60 * 1000);
```

## 📊 Database Schema

### `races` table
- `id`: Primary key
- `meeting_name`: Track name
- `race_number`: Race number
- `race_time`: Scheduled start time
- `status`: Race status
- `active_runner_count`: Number of confirmed starters

### `runners` table
- `id`: Primary key
- `race_id`: Foreign key to races
- `dog_name`: Dog's name
- `box_number`: Starting box
- `fixed_odds`: Fixed win odds
- `is_scratched`: Scratching status

## 🐛 Troubleshooting

### Scraper not working
1. Check GitHub Actions logs for errors
2. Verify Supabase credentials in GitHub Secrets
3. Inspect the website HTML structure (may have changed)

### Frontend not loading data
1. Check browser console for errors
2. Verify Supabase credentials in `index.html`
3. Check Supabase RLS policies are set correctly

### No races showing
1. Verify data exists in Supabase tables
2. Check that race times are in the future
3. Confirm active_runner_count is 4 or 5

## 📄 License

This project is for educational purposes. Please ensure compliance with:
- The Greyhound Recorder's terms of service
- Applicable web scraping laws in your jurisdiction
- Responsible gambling practices

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**Disclaimer**: This tool is for informational purposes only. Always gamble responsibly.
