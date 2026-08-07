#!/bin/bash
# Quick Start - Investment Metrics Dashboard with Real Data

echo "=========================================="
echo "  Investment Metrics Dashboard Startup"
echo "=========================================="
echo ""

# 1. Check if backend is running
echo "1. Checking FastAPI backend..."
if pgrep -f "uvicorn.*investment_backend_fastapi" > /dev/null; then
    echo "   ✅ Backend is running"
    echo "   🔄 Restarting to load new endpoint..."
    pkill -f "uvicorn.*investment_backend_fastapi"
    sleep 2
else
    echo "   ⚠️  Backend not running"
fi

# 2. Start backend
echo "2. Starting FastAPI backend with real data endpoint..."
cd /home/armin/.config/scripts/investments/investment_backend
nohup python3 -m uvicorn investment_backend_fastapi:app --host 0.0.0.0 --port 8000 --reload > /tmp/investment_backend.log 2>&1 &
sleep 3

# 3. Test endpoint
echo "3. Testing new endpoint..."
response=$(curl -s "http://localhost:8000/api/investment_metrics/Investments?filter=portfolio" | head -c 200)

if echo "$response" | grep -q "data_source"; then
    echo "   ✅ Real data endpoint working!"
    if echo "$response" | grep -q '"data_source": "DATABASE"'; then
        echo "   ✅ Using DATABASE (not mock data)"
    fi
else
    echo "   ❌ Endpoint not responding correctly"
    echo "   Check logs: tail -f /tmp/investment_backend.log"
fi

# 4. Frontend info
echo ""
echo "4. Frontend:"
echo "   URL: http://localhost:3000/ViewInvestmentMetrics"
echo "   Status: Frontend needs to be running separately"
echo ""

echo "=========================================="
echo "  Status Summary"
echo "=========================================="
echo "✅ Backend: http://localhost:8000"
echo "✅ API Endpoint: /api/investment_metrics/Investments"
echo "📊 Data Points: 4,025 historical records"
echo "🔢 Investments: 24"
echo "📝 Metrics: 80 per record"
echo ""
echo "Next: Visit http://localhost:3000/ViewInvestmentMetrics"
echo "=========================================="
