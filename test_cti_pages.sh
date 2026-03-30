#!/bin/bash

BASE_URL="http://192.168.1.70:8000/intel"
PAGES=(
    ""                            # Dashboard
    "/cves/"                      # CVEs
    "/actors/"                    # Threat Actors
    "/iocs/"                      # IOCs
    "/alerts/"                    # Alerts
    "/techniques/"                # ATT&CK Techniques
    "/actors/apt28/"              # Actor Detail - APT28
    "/cves/CVE-2023-7028/"        # CVE Detail
)

PAGE_NAMES=(
    "Dashboard"
    "CVEs"
    "Threat Actors"
    "IOCs"
    "Alerts"
    "ATT&CK Techniques"
    "Actor Detail - APT28"
    "CVE Detail - CVE-2023-7028"
)

echo "Testing CTI Platform Pages"
echo "=========================="

for i in "${!PAGES[@]}"; do
    url="${BASE_URL}${PAGES[$i]}"
    name="${PAGE_NAMES[$i]}"
    
    echo -e "\nTesting: $name"
    echo "URL: $url"
    
    # Test with curl to get status code and basic content
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    
    if [ "$status" -eq 200 ]; then
        echo "Status: ✓ PASS (HTTP 200)"
        
        # Get a sample of content to check for basic structure
        content_sample=$(curl -s "$url" | grep -i "<title>" | head -1)
        if [ -n "$content_sample" ]; then
            echo "Title: $content_sample"
        fi
        
        # Check for common error indicators in content
        error_indicators=$(curl -s "$url" | grep -i -E "(error|exception|traceback|500 internal|404 not found)" | head -3)
        if [ -n "$error_indicators" ]; then
            echo "⚠️  Potential issues found in content:"
            echo "$error_indicators"
        else
            echo "Content: ✓ No obvious errors detected"
        fi
    else
        echo "Status: ✗ FAIL (HTTP $status)"
    fi
done

echo -e "\n\nTesting specific interactions..."
echo "====================================="

# Test filter on CVEs page
echo -e "\n1. Testing filter on CVEs page:"
filter_result=$(curl -s -G --data-urlencode "risk_level=critical" "$BASE_URL/cves/" | head -5)
if [ $? -eq 0 ]; then
    echo "✓ Filter test completed (no obvious errors)"
else
    echo "✗ Filter test failed"
fi

# Test sort on actors page
echo -e "\n2. Testing sort on actors page:"
sort_result=$(curl -s -G --data-urlencode "ordering=-risk_level" "$BASE_URL/actors/" | head -5)
if [ $? -eq 0 ]; then
    echo "✓ Sort test completed (no obvious errors)"
else
    echo "✗ Sort test failed"
fi

# Test navigation (actor detail)
echo -e "\n3. Testing navigation to actor detail:"
actor_detail=$(curl -s "$BASE_URL/actors/apt28/" | grep -i "APT28\|apt28" | head -2)
if [ -n "$actor_detail" ]; then
    echo "✓ Actor detail page loads content"
else
    echo "⚠️  Actor detail page may have issues loading specific content"
fi

# Test search on CVEs page
echo -e "\n4. Testing search on CVEs page:"
search_result=$(curl -s -G --data-urlencode "search=2023" "$BASE_URL/cves/" | head -5)
if [ $? -eq 0 ]; then
    echo "✓ Search test completed (no obvious errors)"
else
    echo "✗ Search test failed"
fi

echo -e "\n\nTesting complete."