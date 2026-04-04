# Webhooks — Zapier

## Webhook Types

| Type | Direction | Use Case |
|------|-----------|----------|
| **Catch Hook** | Incoming | Receive data from external systems |
| **Catch Raw Hook** | Incoming | Receive non-JSON data (XML, CSV) |
| **Retrieve Poll** | Incoming (Pull) | Fetch data from URL on schedule |
| **POST/PUT/GET** | Outgoing | Send data to external systems |
| **Custom Request** | Outgoing | Full control over HTTP request |

## Incoming Webhooks

### Catch Hook (JSON)

**Setup:**
```
Trigger: Webhooks by Zapier
Event: Catch Hook
```

Zapier provides webhook URL:
```
https://hooks.zapier.com/hooks/catch/123456/abcdef/
```

**Test with curl:**
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "event": "user.created",
    "user": {
      "id": 12345,
      "email": "john@example.com",
      "name": "John Doe",
      "plan": "premium"
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }' \
  "https://hooks.zapier.com/hooks/catch/123456/abcdef/"
```

**Response:**
```json
{
  "id": "abc123",
  "request_id": "xyz789",
  "status": "success"
}
```

### With Query Parameters

```bash
curl -X POST \
  "https://hooks.zapier.com/hooks/catch/123456/abcdef/?source=shopify&event=order" \
  -H "Content-Type: application/json" \
  -d '{"order_id": 9999, "total": 149.99}'
```

Access in Zap:
- `{{querystring__source}}` → shopify
- `{{querystring__event}}` → order
- `{{order_id}}` → 9999

### Catch Raw Hook

For non-JSON payloads (XML, CSV, custom formats).

**Setup:**
```
Trigger: Webhooks by Zapier
Event: Catch Raw Hook
```

**Receive XML:**
```bash
curl -X POST \
  -H "Content-Type: application/xml" \
  -d '<?xml version="1.0"?>
  <order>
    <id>12345</id>
    <customer>john@example.com</customer>
  </order>' \
  "https://hooks.zapier.com/hooks/catch/123456/raw/"
```

Access: `{{raw_body}}` contains entire payload as string.
Parse with Code step or Formatter.

### Retrieve Poll

Pull data from any URL on Zapier's schedule.

**Setup:**
```
Trigger: Webhooks by Zapier
Event: Retrieve Poll
URL: https://api.yourapp.com/new-orders
Headers: Authorization: Bearer YOUR_API_KEY
```

Zapier polls every 1-15 minutes depending on plan.

**Expected Response:**
```json
[
  {"id": 1, "name": "Order 1"},
  {"id": 2, "name": "Order 2"}
]
```

Each array item triggers the Zap once.

## Outgoing Webhooks

### POST Request

**Action:**
```
Action: Webhooks by Zapier
Event: POST
URL: https://api.yourapp.com/webhook
Payload Type: JSON
Data:
  event: new_user
  user_id: {{trigger.id}}
  email: {{trigger.email}}
  timestamp: {{zap_meta_human_now}}
```

### With Authentication

**API Key in Header:**
```
Headers:
  Authorization: Bearer YOUR_API_KEY
  X-Custom-Header: value
```

**Basic Auth:**
```
Basic Auth:
  Username: api_user
  Password: api_secret
```

### PUT Request

```
Action: Webhooks by Zapier
Event: PUT
URL: https://api.yourapp.com/users/{{trigger.user_id}}
Payload Type: JSON
Data:
  status: active
  updated_at: {{zap_meta_human_now}}
```

### GET Request

```
Action: Webhooks by Zapier
Event: GET
URL: https://api.yourapp.com/users/{{trigger.user_id}}
Headers:
  Authorization: Bearer YOUR_API_KEY
```

### Custom Request

Full control over HTTP method, headers, and body.

```
Action: Webhooks by Zapier
Event: Custom Request
Method: PATCH
URL: https://api.yourapp.com/orders/{{trigger.order_id}}
Headers:
  Authorization: Bearer YOUR_API_KEY
  Content-Type: application/json
  X-Request-ID: {{zap_meta_id}}
Data (Raw):
  {"status": "shipped", "tracking": "{{trigger.tracking_number}}"}
```

## Response Handling

### Access Response Data

After webhook action, response is available:
- `{{webhook_response.status}}` — HTTP status code
- `{{webhook_response.id}}` — Response body field
- `{{webhook_response.data.user.email}}` — Nested field

### Handle Different Status Codes

```
Path A: Success (2xx)
  Condition: Webhook Response Status Code equals 200
  → Continue normal flow

Path B: Client Error (4xx)
  Condition: Webhook Response Status Code equals 400
  → Log error
  → Send alert

Path C: Server Error (5xx)
  Condition: Webhook Response Status Code greater than 499
  → Retry later
```

## Webhook Security

### Verify Incoming Webhooks

**With Shared Secret:**

Many apps send signature header. Verify in Code step:

```javascript
const crypto = require('crypto');
const secret = 'your_webhook_secret';
const signature = inputData.signature;
const payload = inputData.raw_body;

const expectedSig = crypto
  .createHmac('sha256', secret)
  .update(payload)
  .digest('hex');

output = [{
  valid: signature === expectedSig
}];
```

### IP Allowlisting

Zapier webhook IPs: https://help.zapier.com/hc/en-us/articles/8496288690317

Add to your firewall allowlist for incoming webhooks from Zapier.

## Webhook Best Practices

### 1. Return 200 Quickly

Zapier waits 30 seconds max. If your endpoint is slow:
- Queue the work
- Return 200 immediately
- Process asynchronously

### 2. Handle Retries

Zapier retries failed webhooks with exponential backoff.
Design for idempotency — same webhook twice shouldn't duplicate data.

### 3. Log Everything

```
Action: Create Google Sheets Row
Spreadsheet: Webhook Logs
Data:
  Timestamp: {{zap_meta_human_now}}
  Zap ID: {{zap_meta_id}}
  Trigger Data: {{trigger.raw_body}}
  Response: {{webhook_response}}
```

### 4. Timeout Handling

If target is slow:
```
Action: Webhooks by Zapier
☑️ Unfurl URLs (increases timeout slightly)
```

Or use async pattern:
1. Send webhook
2. Target returns 200 + job_id
3. Separate Zap polls for result

### 5. Test Mode

Always test with non-production data:
```bash
curl -X POST \
  -H "X-Test-Mode: true" \
  -d '{"test": true}' \
  "https://hooks.zapier.com/hooks/catch/123456/abcdef/"
```

Handle in your app:
```python
if request.headers.get('X-Test-Mode'):
    return {"status": "test_success"}
```

## Common Webhook Patterns

### Forward to Multiple Services

```
Trigger: Catch Hook
→ POST to Service A
→ POST to Service B
→ POST to Service C
```

### Transform and Forward

```
Trigger: Catch Hook
→ Code: Transform data
→ POST transformed data
```

### Webhook to Email

```
Trigger: Catch Hook
→ Send Email:
  To: alerts@company.com
  Subject: New webhook: {{trigger.event}}
  Body: {{trigger.raw_body}}
```

### Webhook Chain

```
Zap A:
  Trigger: Form submission
  → POST to Zap B webhook

Zap B:
  Trigger: Catch Hook (from Zap A)
  → Complex processing
  → POST to Zap C webhook
```
