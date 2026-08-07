#!/bin/bash
# Quick installation script for redesigned ViewInvestmentMetrics page

set -e

echo "=========================================="
echo "  ViewInvestmentMetrics Redesign Install"
echo "=========================================="
echo ""

BACKEND_DIR="/home/armin/.config/scripts/investments/investment_backend"
FRONTEND_DIR="/home/armin/.config/scripts/investments/investment_frontend/src/app/ViewInvestmentMetrics"

# Step 1: Backup old page
echo "1. Backing up old frontend page..."
cd "$FRONTEND_DIR"
if [ -f "page.tsx" ]; then
    cp page.tsx "page_old_$(date +%Y%m%d_%H%M%S).tsx"
    echo "   ✓ Backup created"
else
    echo "   ⚠ No existing page.tsx found"
fi

# Step 2: Install new page
echo ""
echo "2. Installing redesigned page..."
if [ -f "page_redesigned.tsx" ]; then
    cp page_redesigned.tsx page.tsx
    echo "   ✓ New page installed"
else
    echo "   ❌ page_redesigned.tsx not found!"
    exit 1
fi

# Step 3: Add backend endpoint
echo ""
echo "3. Adding individual investment endpoint to backend..."
cd "$BACKEND_DIR"

# Check if endpoint already exists
if grep -q "investment_metrics_by_name" investment_backend_fastapi.py; then
    echo "   ℹ Endpoint already exists, skipping"
else
    # Find the line number after /investment_metrics endpoint
    LINE_NUM=$(grep -n '@investment_api.get("/dashboard_charts/' investment_backend_fastapi.py | cut -d: -f1 | head -1)
    
    if [ -z "$LINE_NUM" ]; then
        echo "   ❌ Could not find insertion point in investment_backend_fastapi.py"
        exit 1
    fi
    
    # Backup
    cp investment_backend_fastapi.py "investment_backend_fastapi.py.backup_$(date +%Y%m%d_%H%M%S)"
    echo "   ✓ Backend backed up"
    
    # Insert new endpoint (would need the actual code here)
    echo "   ⚠ Manual step required:"
    echo "      Add content from NEW_INDIVIDUAL_ENDPOINT.py"
    echo "      to investment_backend_fastapi.py at line $LINE_NUM"
fi

# Step 4: Check dependencies
echo ""
echo "4. Checking frontend dependencies..."
cd "$FRONTEND_DIR/../.."  # Go to frontend root

if [ -f "package.json" ]; then
    if grep -q "chart.js" package.json; then
        echo "   ✓ chart.js found"
    else
        echo "   ⚠ Installing chart.js..."
        npm install chart.js react-chartjs-2
    fi
else
    echo "   ❌ package.json not found!"
fi

# Step 5: Summary
echo ""
echo "=========================================="
echo "  Installation Summary"
echo "=========================================="
echo "✓ Old page backed up"
echo "✓ New page installed"
echo "⚠ Manual: Add NEW_INDIVIDUAL_ENDPOINT.py to backend"
echo ""
echo "Next Steps:"
echo "1. Add backend endpoint manually (see guide)"
echo "2. Restart backend: cd $BACKEND_DIR && pkill -f uvicorn && python3 -m uvicorn investment_backend_fastapi:investment_api --host 0.0.0.0 --port 3337 --reload &"
echo "3. Restart frontend: cd ${FRONTEND_DIR}/../.. && npm run dev"
echo "4. Visit: http://localhost:3000/ViewInvestmentMetrics"
echo ""
echo "Documentation: /home/armin/.gemini/antigravity/scratch/NEW_METRICS_PAGE_GUIDE.md"
echo "=========================================="
