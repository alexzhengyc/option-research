#!/bin/bash

# Dashboard Setup Verification Script
# This script checks if everything is properly configured

echo "🔍 Verifying Intraday Dashboard Setup..."
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0

# Check Node.js
echo -n "Checking Node.js... "
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo -e "${GREEN}✓${NC} Found $NODE_VERSION"
else
    echo -e "${RED}✗${NC} Node.js not found"
    ERRORS=$((ERRORS + 1))
fi

# Check npm
echo -n "Checking npm... "
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    echo -e "${GREEN}✓${NC} Found v$NPM_VERSION"
else
    echo -e "${RED}✗${NC} npm not found"
    ERRORS=$((ERRORS + 1))
fi

# Check Supabase CLI
echo -n "Checking Supabase CLI... "
if command -v supabase &> /dev/null; then
    SUPABASE_VERSION=$(supabase --version 2>&1 | head -1)
    echo -e "${GREEN}✓${NC} Found $SUPABASE_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Supabase CLI not found (optional)"
fi

# Check if dependencies are installed
echo -n "Checking node_modules... "
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✓${NC} Dependencies installed"
else
    echo -e "${RED}✗${NC} Dependencies not installed"
    echo "   Run: npm install"
    ERRORS=$((ERRORS + 1))
fi

# Check .env.local
echo -n "Checking .env.local... "
if [ -f ".env.local" ]; then
    echo -e "${GREEN}✓${NC} Environment file exists"
    
    # Check if it has the required variables
    if grep -q "NEXT_PUBLIC_SUPABASE_URL" .env.local && grep -q "NEXT_PUBLIC_SUPABASE_ANON_KEY" .env.local; then
        echo -e "${GREEN}  ✓${NC} Required variables present"
    else
        echo -e "${RED}  ✗${NC} Missing required variables"
        ERRORS=$((ERRORS + 1))
    fi
else
    echo -e "${YELLOW}⚠${NC} .env.local not found"
    echo "   Run: cp .env.example .env.local"
fi

# Check key files
echo ""
echo "Checking key files:"

FILES=(
    "app/page.tsx"
    "components/stats-cards.tsx"
    "components/signals-chart.tsx"
    "components/signals-table.tsx"
    "hooks/useIntradaySignals.ts"
    "lib/supabase.ts"
    "types/supabase.ts"
)

for file in "${FILES[@]}"; do
    echo -n "  $file... "
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check Supabase status
echo ""
echo -n "Checking Supabase status... "
if command -v supabase &> /dev/null; then
    cd .. # Go to project root
    SUPABASE_STATUS=$(supabase status 2>&1)
    if echo "$SUPABASE_STATUS" | grep -q "API URL"; then
        echo -e "${GREEN}✓${NC} Supabase is running"
        
        # Extract and display API URL
        API_URL=$(echo "$SUPABASE_STATUS" | grep "API URL" | awk '{print $3}')
        echo "   API URL: $API_URL"
        
        # Check if data exists
        echo -n "   Checking for intraday signals... "
        # This requires psql or similar, skipping for now
        echo -e "${YELLOW}⚠${NC} Run manually: supabase db reset"
    else
        echo -e "${RED}✗${NC} Supabase not running"
        echo "   Run: supabase start"
        ERRORS=$((ERRORS + 1))
    fi
    cd dashboard
else
    echo -e "${YELLOW}⚠${NC} Cannot check (Supabase CLI not installed)"
fi

# Try to build
echo ""
echo -n "Testing build... "
BUILD_OUTPUT=$(npm run build 2>&1)
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Build successful"
else
    echo -e "${RED}✗${NC} Build failed"
    echo "$BUILD_OUTPUT" | tail -20
    ERRORS=$((ERRORS + 1))
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed!${NC}"
    echo ""
    echo "You're ready to go! Run:"
    echo "  npm run dev"
    echo ""
    echo "Then open: http://localhost:3000"
else
    echo -e "${RED}❌ $ERRORS error(s) found${NC}"
    echo ""
    echo "Please fix the errors above and try again."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exit $ERRORS

