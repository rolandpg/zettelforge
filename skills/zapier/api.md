# REST Hooks API — Zapier

## Authentication

Get API key from: https://zapier.com/developer/platform

```bash
export ZAPIER_API_KEY="your_api_key_here"

# Test connection
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  https://api.zapier.com/v1/profile
```

## Profile & Account

### Get Profile
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  https://api.zapier.com/v1/profile
```

Response:
```json
{
  "id": 123456,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "timezone": "America/New_York"
}
```

## Zaps Management

### List All Zaps
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/zaps"
```

### Get Zap Details
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/zaps/ZAP_ID"
```

### Get Zap Runs (History)
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/zaps/ZAP_ID/runs?limit=10"
```

### Turn Zap On
```bash
curl -X PUT \
  -H "Authorization: Bearer $ZAPIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": true}' \
  "https://api.zapier.com/v1/zaps/ZAP_ID"
```

### Turn Zap Off
```bash
curl -X PUT \
  -H "Authorization: Bearer $ZAPIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"is_enabled": false}' \
  "https://api.zapier.com/v1/zaps/ZAP_ID"
```

## Apps & Authentication

### List Connected Apps
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/apps"
```

### Get App Details
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/apps/APP_SLUG"
```

### List App Authentications
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/authentications"
```

## AI Actions (for LLM Integration)

Zapier provides AI Actions for LLM integrations (ChatGPT, Claude, etc.).

### Get Available Actions
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://actions.zapier.com/api/v1/exposed/"
```

### Execute AI Action
```bash
curl -X POST \
  -H "Authorization: Bearer $ZAPIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Send a Slack message to #general saying Hello"
  }' \
  "https://actions.zapier.com/api/v1/run/ACTION_ID/"
```

### List AI Action Logs
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://actions.zapier.com/api/v1/logs/"
```

## Natural Language Actions (NLA)

For AI assistants to control Zapier with natural language.

### Available via OpenAI Plugin
- Configure at: https://actions.zapier.com/gpt/
- Exposes your Zaps as natural language actions

### Direct NLA Endpoint
```bash
curl -X POST \
  -H "Authorization: Bearer $ZAPIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instructions": "Create a Google Calendar event tomorrow at 3pm called Team Standup"
  }' \
  "https://nla.zapier.com/api/v1/run/"
```

## Rate Limits

| Plan | Requests/min | Requests/day |
|------|--------------|--------------|
| Free | 10 | 1,000 |
| Starter | 20 | 5,000 |
| Professional | 50 | 25,000 |
| Team | 100 | 100,000 |

## Error Handling

### Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 401 | Invalid API key | Check ZAPIER_API_KEY |
| 403 | Permission denied | Check app permissions |
| 404 | Resource not found | Verify Zap/resource ID |
| 429 | Rate limited | Wait and retry |
| 500 | Server error | Retry with backoff |

### Error Response Format
```json
{
  "errors": [
    {
      "code": "INVALID_REQUEST",
      "message": "The request was invalid",
      "field": "trigger_id"
    }
  ]
}
```

## Pagination

All list endpoints support pagination:

```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/zaps?offset=0&limit=20"
```

Parameters:
- `offset`: Starting position (default 0)
- `limit`: Number of results (default 20, max 100)

## Webhooks API

### Subscribe to Zap Events
```bash
curl -X POST \
  -H "Authorization: Bearer $ZAPIER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://your-server.com/webhooks/zapier",
    "event": "zap.run.completed"
  }' \
  "https://api.zapier.com/v1/hooks"
```

### Webhook Events

| Event | Description |
|-------|-------------|
| `zap.run.completed` | Zap finished running |
| `zap.run.errored` | Zap encountered error |
| `zap.turned_off` | Zap was disabled |
| `zap.turned_on` | Zap was enabled |

### List Active Hooks
```bash
curl -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/hooks"
```

### Delete Hook
```bash
curl -X DELETE \
  -H "Authorization: Bearer $ZAPIER_API_KEY" \
  "https://api.zapier.com/v1/hooks/HOOK_ID"
```
