#!/bin/bash
# Test script for pre-commit hook validation
# Tests both valid and invalid migration files

set -e

HOOK_PATH=".githooks/pre-commit"
TEST_DIR=$(mktemp -d)
trap "rm -rf $TEST_DIR" EXIT

echo "🧪 Testing pre-commit hook..."

# Initialize test git repo
cd "$TEST_DIR"
git init
git config user.email "test@example.com"
git config user.name "Test User"
mkdir -p migrations

# Configure to use the hook from the original repo
git config core.hooksPath "$(cd /Users/pascalliu/Sites/claude-workflow-kit && pwd)/.githooks"

TEST_PASSED=0
TEST_FAILED=0

# Test 1: Valid migration with IF NOT EXISTS
echo ""
echo "Test 1: Valid migration with CREATE TABLE IF NOT EXISTS"
cat > migrations/001_create_users.sql << 'EOF'
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
EOF
git add migrations/001_create_users.sql
if git commit -m "Valid migration" 2>/dev/null; then
    echo "✅ Test 1 PASSED: Valid migration accepted"
    ((TEST_PASSED++))
else
    echo "❌ Test 1 FAILED: Valid migration rejected"
    ((TEST_FAILED++))
fi

# Reset for next test
git reset --soft HEAD~1 2>/dev/null || true
rm -f migrations/*.sql

# Test 2: Invalid migration without IF NOT EXISTS (CREATE TABLE)
echo ""
echo "Test 2: Invalid migration with CREATE TABLE (no IF NOT EXISTS)"
cat > migrations/002_bad_table.sql << 'EOF'
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
EOF
git add migrations/002_bad_table.sql
if ! git commit -m "Invalid migration" 2>/dev/null; then
    echo "✅ Test 2 PASSED: Invalid CREATE TABLE rejected"
    ((TEST_PASSED++))
else
    echo "❌ Test 2 FAILED: Invalid CREATE TABLE accepted"
    ((TEST_FAILED++))
fi

# Reset for next test
git reset --hard HEAD 2>/dev/null || true
rm -f migrations/*.sql

# Test 3: Invalid migration with DROP statement
echo ""
echo "Test 3: Invalid migration with DROP statement"
cat > migrations/003_drop_table.sql << 'EOF'
DROP TABLE IF EXISTS old_users;
EOF
git add migrations/003_drop_table.sql
if ! git commit -m "Drop migration" 2>/dev/null; then
    echo "✅ Test 3 PASSED: DROP statement rejected"
    ((TEST_PASSED++))
else
    echo "❌ Test 3 FAILED: DROP statement accepted"
    ((TEST_FAILED++))
fi

# Reset for next test
git reset --hard HEAD 2>/dev/null || true
rm -f migrations/*.sql

# Test 4: Valid migration with CREATE INDEX IF NOT EXISTS
echo ""
echo "Test 4: Valid migration with CREATE INDEX IF NOT EXISTS"
cat > migrations/004_create_index.sql << 'EOF'
CREATE INDEX IF NOT EXISTS idx_users_name ON users(name);
EOF
git add migrations/004_create_index.sql
if git commit -m "Valid index migration" 2>/dev/null; then
    echo "✅ Test 4 PASSED: Valid CREATE INDEX IF NOT EXISTS accepted"
    ((TEST_PASSED++))
else
    echo "❌ Test 4 FAILED: Valid CREATE INDEX IF NOT EXISTS rejected"
    ((TEST_FAILED++))
fi

# Reset for next test
git reset --soft HEAD~1 2>/dev/null || true
rm -f migrations/*.sql

# Test 5: Invalid migration with CREATE INDEX (no IF NOT EXISTS)
echo ""
echo "Test 5: Invalid migration with CREATE INDEX (no IF NOT EXISTS)"
cat > migrations/005_bad_index.sql << 'EOF'
CREATE INDEX idx_users_email ON users(email);
EOF
git add migrations/005_bad_index.sql
if ! git commit -m "Invalid index migration" 2>/dev/null; then
    echo "✅ Test 5 PASSED: Invalid CREATE INDEX rejected"
    ((TEST_PASSED++))
else
    echo "❌ Test 5 FAILED: Invalid CREATE INDEX accepted"
    ((TEST_FAILED++))
fi

# Reset for next test
git reset --hard HEAD 2>/dev/null || true
rm -f migrations/*.sql

# Test 6: Non-migration files should not be checked
echo ""
echo "Test 6: Non-migration SQL files should pass hook"
mkdir -p lib
cat > lib/query.sql << 'EOF'
CREATE TABLE temp_table (id INT);
EOF
git add lib/query.sql
if git commit -m "Non-migration SQL" 2>/dev/null; then
    echo "✅ Test 6 PASSED: Non-migration SQL files ignored"
    ((TEST_PASSED++))
else
    echo "❌ Test 6 FAILED: Non-migration SQL files not ignored"
    ((TEST_FAILED++))
fi

# Summary
echo ""
echo "================================"
echo "Test Results:"
echo "  Passed: $TEST_PASSED"
echo "  Failed: $TEST_FAILED"
echo "================================"

if [ $TEST_FAILED -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ Some tests failed!"
    exit 1
fi
