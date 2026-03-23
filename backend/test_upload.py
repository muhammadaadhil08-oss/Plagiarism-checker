import requests

url = "http://127.0.0.1:5000/extract-text"
files = {'file': ('test.pdf', b'%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/MediaBox [ 0 0 200 200 ]\n/Count 1\n/Kids [ 3 0 R ]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/Resources <<\n/Font <<\n/F1 4 0 R\n>>\n>>\n/Contents 5 0 R\n>>\nendobj\n4 0 obj\n<<\n/Type /Font\n/Subtype /Type1\n/BaseFont /Times-Roman\n>>\nendobj\n5 0 obj\n<< /Length 44 >>\nstream\nBT\n70 50 TD\n/F1 12 Tf\n(Test PDF Document) Tj\nET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000056 00000 n \n0000000145 00000 n \n0000000244 00000 n \n0000000329 00000 n \ntrailer\n<<\n/Size 6\n/Root 1 0 R\n>>\nstartxref\n422\n%%EOF')}
response = requests.post(url, files=files)
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
