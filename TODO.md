# Investment App - Comprehensive Enhancement Plan

## Phase 1: Fix Edit Page ✅
- [ ] Fix EditInvestmentData page - ensure CRUD works with proper notifications
- [ ] Add success/error snackbar notifications for all operations
- [ ] Add confirmation dialogs for deletes
- [ ] Fix any API routing issues

## Phase 2: Unit Price Extraction Enhancement
- [ ] Fix yfinance backfill to get ALL historical prices when investment is first added
- [ ] Fix profiledata scraper to use Playwright properly on funds.profiledata.co.za
- [ ] Add backfill cursor logic for profiledata (10 days at a time)
- [ ] Store intermediate unit prices for predictions

## Phase 3: Factsheet/MDD Page
- [ ] Build factsheet viewing page with year/month/investment filtering
- [ ] Store factsheets in database
- [ ] Monthly auto-download via Playwright
- [ ] View historic factsheets

## Phase 4: Upgrade Metrics
- [ ] Per investment metrics
- [ ] Per investment type (ETF, Unit Trust, etc.)
- [ ] Per institution
- [ ] Per account type (Tax Free, RA, Discretionary)
- [ ] Per currency

## Phase 5: Property Investment Expansion
- [ ] Comprehensive property calculator (IRR, Net/Gross Yield, Bond, CGT, etc.)
- [ ] Property URL scraping with Playwright
- [ ] PDF report generation
- [ ] Break-even analysis, sensitivity analysis
- [ ] Monte Carlo for property

## Phase 6: Monte Carlo Simulation
- [ ] Add Monte Carlo to predictions page
- [ ] GBM-based simulation
- [ ] Portfolio-level Monte Carlo

## Phase 7: Testing & Verification
- [ ] Test unit price extraction (yfinance + profiledata)
- [ ] Test factsheet download/store/view
- [ ] Verify IRR, net worth calculations
- [ ] Verify docker-compose works
