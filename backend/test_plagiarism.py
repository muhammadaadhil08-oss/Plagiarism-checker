
import json
import re
import http.cookiejar
import urllib.request
import urllib.parse

# Create a cookie jar and opener to maintain session
cookie_jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

print("=" * 60)
print("Testing Plagiarism Check Flow")
print("=" * 60)

try:
    # Test 1: Check plagiarism with similar documents
    data = {
        'text1': 'The quick brown fox jumps over the lazy dog and the moon shines bright',
        'text2': 'The quick brown fox jumps over the lazy dog and stars shine bright'
    }
    
    encoded_data = urllib.parse.urlencode(data).encode('utf-8')
    check_req = urllib.request.Request('http://localhost:5000/check', data=encoded_data)
    check_response = opener.open(check_req)
    result = json.loads(check_response.read().decode('utf-8'))
    
    print('\n✓ Check endpoint response:')
    print(json.dumps(result, indent=2))
    
    # Test 2: Access analysis page with session
    print("\nFetching analysis page...")
    analysis_req = urllib.request.Request('http://localhost:5000/analysis')
    analysis_response = opener.open(analysis_req)
    analysis_html = analysis_response.read().decode('utf-8')
    
    if 'Similarity Found' in analysis_html:
        print('✓ Analysis page shows "Similarity Found" text')
        
        # Extract the similarity percentage
        match = re.search(r'<div class="circle">(\d+)%</div>', analysis_html)
        if match:
            similarity_pct = match.group(1)
            print(f'✓ Similarity percentage displayed: {similarity_pct}%')
            
            # Verify it matches what the check endpoint returned
            if result.get('data', {}).get('similarity') == int(similarity_pct):
                print('✓ PASS: Analysis page displays correct similarity from /check endpoint')
            else:
                print('✗ FAIL: Similarity mismatch between /check and /analysis')
        else:
            print('✗ Could not extract similarity percentage from HTML')
    else:
        print('✗ Analysis page not showing "Similarity Found" text')
        
except Exception as e:
    print(f'✗ Error: {e}')
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
