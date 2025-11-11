# HOW TO LOAD THE EA INTO METATRADER 5

## Quick Start Guide - 5 Steps to Auto-Trading

---

## STEP 1: Open MetaTrader 5 Data Folder

1. Open **MetaTrader 5**
2. Click **File** → **Open Data Folder**

   ![File Menu Location]
   ```
   Top menu bar:
   File | View | Insert | Charts | Tools | Window | Help
   ```

3. A Windows Explorer window will open

---

## STEP 2: Copy the EA File

1. In the opened folder, navigate to:
   ```
   MQL5 → Experts
   ```

2. Copy the file `UltimateHybridEA.mq5` from your computer to this **Experts** folder

   **Where to get the file:**
   - It's in your git repository: `/home/user/tradelocker/UltimateHybridEA.mq5`
   - Or download from your git branch: `claude/review-formula-011CUzm5ETmk28W61g8GCvNn`

3. Your folder should now look like:
   ```
   MQL5/
   └── Experts/
       └── UltimateHybridEA.mq5  ← Your file here!
   ```

**OPTIONAL - Also install the Indicator:**
   - Navigate to: `MQL5 → Indicators`
   - Copy `UltimateHybridPro.mq5` there
   - This gives you visual arrows (good for manual trading)

---

## STEP 3: Compile the EA

1. In MT5, press **F4** to open **MetaEditor**

2. In MetaEditor, look at the left panel (**Navigator**)

3. Expand the tree:
   ```
   MQL5
   └── Experts
       └── UltimateHybridEA.mq5  ← Find this
   ```

4. **Double-click** on `UltimateHybridEA.mq5`
   - The code will open in the editor

5. Press **F7** to compile
   - Or click **Compile** button (toolbar icon)

6. Check the **Toolbox** panel at bottom:
   ```
   ✅ GOOD: "0 error(s), 0 warning(s)" in green
   ❌ BAD: Any red errors (let me know if you see any)
   ```

7. Close MetaEditor (or keep it open)

---

## STEP 4: Add EA to Chart

### A. Open a Chart

1. In MT5 main window, press **Ctrl+U** to open **Market Watch**

2. Find **EURUSD** (or your preferred pair)

3. **Right-click** on EURUSD → **Chart Window** → **H1** (1-hour timeframe)

### B. Attach the EA

1. Look at the **Navigator** panel (left side of MT5)
   - If not visible, press **Ctrl+N**

2. Expand the tree:
   ```
   Navigator
   └── Expert Advisors
       └── UltimateHybridEA  ← Your EA!
   ```

3. **DRAG** `UltimateHybridEA` onto your EURUSD chart

4. A settings window will pop up:

---

## STEP 5: Configure Settings

When the settings window appears:

### **Inputs Tab** (Configure These):

```
Lot Size:                  0.01        ← Start SMALL on demo!
Risk Percent:              2.0         ← 2% risk per trade
Use Auto Lot:              true        ← Let EA calculate size
Confidence Threshold:      0.75        ← 75% minimum (recommended)
Stop Loss Pips:            50          ← Manual SL (if needed)
Risk Reward Ratio:         2.0         ← Target 2× risk
Use Partial Exit:          true        ← Take 50% profit early
Partial Exit Percent:      50.0        ← Exit 50% at 1.5R
Partial Exit R:R:          1.5         ← First exit at 1.5R
Magic Number:              123456      ← Unique ID (leave as is)
Trade On New Bar Only:     true        ← Wait for bar close
Max Trades Per Day:        3           ← Don't overtrade
```

**Recommended Settings for Demo Testing:**
- **Confidence Threshold:** `0.75` (75%)
- **Risk Percent:** `2.0` (2%)
- **Use Auto Lot:** `true`
- **Max Trades Per Day:** `3`

### **Common Tab**:

Check these boxes:
- ✅ **Allow live trading**
- ✅ **Allow DLL imports** (if needed)
- ✅ **Allow trading signals**

Click **OK**!

---

## STEP 6: Enable Auto Trading

After EA is on chart:

1. Look at **top toolbar** in MT5

2. Find the **"Auto Trading"** button
   ```
   It looks like: [▶] or [Auto Trading]
   ```

3. **Click it** to enable
   - Should turn **GREEN** when active
   - If red, EA won't trade!

4. Check chart - you should see in **top-right corner**:
   ```
   UltimateHybridEA
   Confidence: 75%
   Status: Waiting for signal...
   ```

---

## ✅ SUCCESS! EA is Now Running!

The EA will:
- Analyze market every hour (H1 bar closes)
- Generate signals when confidence ≥ 75%
- Automatically open trades
- Manage stop loss & take profit
- Close trades when targets hit
- Show all trades in **Trade** and **History** tabs

---

## 🎯 HOW TO VERIFY IT'S WORKING

### Check #1: Expert Tab
1. Look at bottom of MT5: **Toolbox** panel
2. Click **Experts** tab
3. You should see messages like:
   ```
   2024.11.11 20:00:00   UltimateHybridEA  Ultimate Hybrid EA initialized
   2024.11.11 20:00:00   UltimateHybridEA  Confidence Threshold: 0.75
   2024.11.11 20:00:00   UltimateHybridEA  Risk per trade: 2%
   ```

### Check #2: Journal Tab
1. Click **Journal** tab (next to Experts)
2. Should show:
   ```
   Expert UltimateHybridEA loaded successfully
   ```

### Check #3: Auto Trading Icon
- **GREEN** = Active ✅
- **RED** = Disabled ❌

---

## 🚨 TROUBLESHOOTING

### Problem: EA not appearing in Navigator

**Solution:**
1. Make sure file is in correct folder: `MQL5/Experts/`
2. Refresh Navigator: Right-click in Navigator → **Refresh**
3. Restart MT5

### Problem: "0 experts loaded" message

**Solution:**
1. Check if file compiled: Open MetaEditor (F4) → Compile (F7)
2. Look for errors in Toolbox
3. Make sure file extension is `.mq5` (not `.txt` or `.mq5.txt`)

### Problem: EA shows but won't trade

**Solution:**
1. Check **Auto Trading** button is GREEN
2. Check EA settings: Right-click chart → **Expert Advisors** → **Properties**
3. Verify "Allow live trading" is checked
4. Check if it's demo account (some EAs won't work on live until tested)

### Problem: "Trade is not allowed" error

**Solution:**
1. Go to **Tools** → **Options** → **Expert Advisors**
2. Check: ✅ **Allow automated trading**
3. Check: ✅ **Allow DLL imports**
4. Click OK, restart MT5

### Problem: Compile errors

**Solution:**
1. Copy the exact error message
2. Send it to me - I'll fix the code
3. Or check if MT5 is up to date (needs MQL5 build 3650+)

---

## 📊 MONITORING YOUR EA

### Where to See Trades:

**1. Trade Tab (Bottom Panel)**
- Shows currently **OPEN** trades
- See floating P/L in real-time

**2. History Tab (Bottom Panel)**
- Shows **CLOSED** trades
- Right-click → **Period** → select date range
- See all past trades with P/L

**3. Account History Report**
- Right-click in **History** → **Report**
- Gets detailed HTML report
- Shows equity curve, stats, etc.

### Important Info Displayed:

On your chart (top-right corner):
```
UltimateHybridEA
Balance: $10,000.00
Confidence: 75%
Trades Today: 1/3
Last Signal: BUY at 1.1234 (80% confidence)
```

---

## ⚙️ ADJUSTING SETTINGS LATER

To change settings after EA is loaded:

1. **Right-click** on chart
2. **Expert Advisors** → **Properties**
3. Change any settings
4. Click **OK**

**OR:**

1. Remove EA from chart (right-click → **Expert Advisors** → **Remove**)
2. Drag it onto chart again
3. Configure fresh

---

## 🎓 TESTING CHECKLIST

Before relying on EA:

- [ ] Installed on **DEMO account** first
- [ ] Auto Trading button is **GREEN**
- [ ] Confidence threshold set to **0.75**
- [ ] Risk percent set to **2%**
- [ ] Checked **Experts** tab for messages
- [ ] Waited for at least **1 signal** to confirm it works
- [ ] Verified trades appear in **Trade/History** tabs
- [ ] Monitored for at least **3 months** on demo
- [ ] Kept trading journal
- [ ] Account is **growing** not shrinking

**Only after ALL boxes checked → Consider live trading!**

---

## 📁 QUICK REFERENCE

### File Locations:

```
📂 MetaTrader 5 Data Folder/
├── 📂 MQL5/
│   ├── 📂 Experts/
│   │   └── UltimateHybridEA.mq5      ← EA goes here
│   └── 📂 Indicators/
│       └── UltimateHybridPro.mq5     ← Indicator goes here (optional)
```

### Keyboard Shortcuts:

- **Ctrl+U** = Market Watch
- **Ctrl+N** = Navigator
- **Ctrl+T** = Toolbox (Trade/History)
- **F4** = MetaEditor
- **F7** = Compile (in MetaEditor)

---

## 🎯 NEXT STEPS

Once EA is loaded:

1. **Let it run on DEMO** for 1 week
2. **Check daily** for trades
3. **Monitor performance** in History tab
4. **Compare to simulation** results
5. **After 3 months**, evaluate:
   - Is it profitable?
   - Is drawdown acceptable?
   - Is win rate reasonable?
6. **Only then** consider small live account

---

## 💬 NEED HELP?

If you get stuck:

1. **Take a screenshot** of the error/issue
2. **Check Experts tab** for error messages
3. **Send me:**
   - What step you're on
   - What error you see
   - Screenshot if possible

I'll help you troubleshoot!

---

## 🎉 YOU'RE READY!

Follow these steps and you'll have the EA running in 5-10 minutes!

**Remember:**
- ✅ Start on DEMO
- ✅ Risk only 2% per trade
- ✅ Test for 3+ months
- ✅ Keep trading journal
- ✅ Be patient

**Good luck with your automated trading!** 🚀📈

---

*Need the files? They're in your git repository at:*
- `/home/user/tradelocker/UltimateHybridEA.mq5`
- `/home/user/tradelocker/UltimateHybridPro.mq5`
- `/home/user/tradelocker/MT5_INSTALLATION_GUIDE.md`
