# OCR Integration Patterns

## Huawei Cloud OCR API

Huawei Cloud provides multiple OCR services. Select based on document type:

| Service | Use Case | Region Availability |
|---------|----------|-------------------|
| General Text OCR | Printed documents, contracts, invoices | Most regions |
| Handwriting OCR | Scanned handwritten forms | Limited regions |
| Business Card OCR | Contact information extraction | Most regions |
| Table OCR | Structured table extraction | Most regions |

## Authentication

OCR API uses AK/SK with HMAC-SHA256 signing. The signature process:

1. Construct canonical request string
2. Create string to sign with timestamp
3. Calculate HMAC-SHA256 signature
4. Add Authorization header to request

```python
import hashlib
import hmac
import datetime

def sign_request(ak, sk, method, url, headers, body=None):
    timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    # ... signing logic per Huawei Cloud API signature spec
    return signed_headers
```

## Cross-Region OCR

Some regions lack specific OCR services. When the target region does not have the required OCR type:

- Use a region that has the service (e.g., `ap-southeast-1` for General Text OCR)
- Add network latency budget to pipeline timing
- Cache OCR results to avoid repeated cross-region calls
- Consider using FunctionGraph in the OCR region to minimize latency

## FunctionGraph OCR Pattern

```python
# FunctionGraph handler for OCR trigger
def handler(event, context):
    # 1. Parse OBS event (bucket, object key)
    bucket = event['records'][0]['s3']['bucket']['name']
    key = event['records'][0]['s3']['object']['key']

    # 2. Read document from OBS
    obs_client = get_obs_client()
    obj = obs_client.getObject(bucket, key, loadStreamInMemory=True)
    content = obj.body.buffer.read()

    # 3. Call OCR API
    ocr_result = call_ocr_api(content)

    # 4. Write extracted text to OBS
    text_key = key.replace('.pdf', '.txt')
    obs_client.putContent(output_bucket, text_key, ocr_result)

    return {'statusCode': 200, 'body': f'OCR complete: {text_key}'}
```

## Error Handling

- **OCR timeout**: Retry with exponential backoff (3 attempts, 2s/4s/8s)
- **OCR quality low**: Log warning, proceed with partial extraction
- **Unsupported format**: Return clear error, do not silently fail
- **Rate limiting**: Implement request throttling (max 10 concurrent OCR calls)

## OBS Trigger Configuration

FunctionGraph can be triggered automatically when objects are created in OBS:

```
Trigger Type: OBS
Bucket: <YOUR_BUCKET_NAME>
Event: ObjectCreated
Prefix: contracts/  (optional filter)
Suffix: .pdf        (optional filter)
Function: ayco-ocr-trigger
```

The trigger invokes the function automatically on upload. No polling required.
