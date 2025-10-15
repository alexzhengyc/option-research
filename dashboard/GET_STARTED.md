# 🚀 Get Started with Intraday Dashboard

Welcome! This guide will get you up and running in **2 minutes**.

## Prerequisites ✓

Make sure you have:
- [x] Node.js 18+ installed
- [x] Local Supabase running
- [x] Some intraday signals in the database

## Quick Start (2 Minutes)

### Step 1: Install Dependencies (60 seconds)

```bash
cd /Users/alexzheng/Documents/GitHub/option-research/dashboard
npm install
```

### Step 2: Environment Setup (30 seconds)

The `.env.local` file should already exist. If not:

```bash
cp .env.example .env.local
```

It should contain:
```env
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0
```

### Step 3: Start Dashboard (10 seconds)

```bash
npm run dev
```

### Step 4: Open Browser

Navigate to: **http://localhost:3000**

## 🎉 That's it!

You should see:
- Dashboard header
- Stats cards (Total Signals, Call/Put breakdown)
- Charts and Tables tabs
- Date filter dropdown

## 📊 What You're Looking At

### Stats Cards (Top Row)
- **Total Signals**: Count of all signals
- **Call Signals**: Green - bullish signals
- **Put Signals**: Red - bearish signals  
- **Avg Dir Score**: Mean directional score

### Charts Tab
1. **Signals by Symbol**: Bar chart showing CALL/PUT/PASS distribution
2. **Directional Score Analysis**: Scatter plot of current vs EWMA scores
3. **Volume Analysis**: Call vs Put volume comparison

### Table Tab
- Complete signal details
- Sortable columns
- Color-coded indicators
- All metrics visible

## 🔄 Generate Sample Data (if needed)

If you see "No signals found":

```bash
# Go to project root
cd /Users/alexzheng/Documents/GitHub/option-research

# Run the intraday pipeline
python jobs/intraday.py
```

This will generate signals that appear in the dashboard.

## 🐛 Quick Troubleshooting

### "Error fetching signals"
**Fix**: Start Supabase
```bash
cd /Users/alexzheng/Documents/GitHub/option-research
supabase start
```

### Port 3000 in use
**Fix**: Use different port
```bash
npm run dev -- -p 3001
```

### Build errors
**Fix**: Reinstall dependencies
```bash
rm -rf node_modules package-lock.json
npm install
```

## 📖 More Information

- **Full Documentation**: See `README.md`
- **Features Guide**: See `FEATURES.md`
- **Quick Reference**: See `QUICKSTART.md`

## 🧪 Verify Setup

Run the verification script:
```bash
./verify-setup.sh
```

This checks:
- ✓ Node.js & npm installed
- ✓ Dependencies installed
- ✓ Environment variables set
- ✓ Key files present
- ✓ Supabase running
- ✓ Build works

## 💡 Pro Tips

1. **Date Filtering**: Use dropdown to view specific days
2. **Switch Views**: Toggle between Charts and Table
3. **Hover Charts**: Hover for detailed tooltips
4. **Auto Refresh**: Refresh browser to see new signals

## 🎯 Next Steps

Once you're comfortable:

1. **Customize Colors**: Edit `app/globals.css`
2. **Add Charts**: Create new chart components
3. **Add Filters**: Extend filtering options
4. **Deploy**: Build and deploy to production

## 📞 Need Help?

Check these files:
- `README.md` - Comprehensive guide
- `FEATURES.md` - Feature documentation  
- `QUICKSTART.md` - Setup walkthrough
- `DASHBOARD_SUMMARY.md` - Project overview

## ✨ Enjoy!

You now have a beautiful, functional dashboard for your intraday signals. Happy trading! 📈

---

**Questions?** Check the documentation files or review the code comments.

