# Triggers — Zapier

## Trigger Types

| Type | Latency | Use Case |
|------|---------|----------|
| **Polling** | 1-15 min | Apps without webhook support |
| **Instant (Webhook)** | Seconds | Real-time needs |
| **Schedule** | Exact time | Recurring tasks |
| **Catch Hook** | Instant | Custom integrations |
| **RSS** | 5-15 min | Blog/feed monitoring |

## Polling vs Instant

### Polling Triggers
- Zapier checks app periodically
- Free plan: every 15 minutes
- Paid plans: every 1-2 minutes
- Examples: New row in Google Sheets, New Salesforce lead

### Instant Triggers (Webhooks)
- App notifies Zapier immediately
- No delay
- Examples: New Stripe payment, New Slack message
- Look for ⚡ icon in Zapier UI

**Always prefer instant triggers when available.**

## Common Trigger Patterns

### New Record Created

**Google Sheets — New Row**
```
Trigger: New Spreadsheet Row
Spreadsheet: [Your Sheet]
Worksheet: [Sheet1]
```

**Airtable — New Record**
```
Trigger: New Record
Base: [Your Base]
Table: [Your Table]
View: [Optional - filter]
```

**Salesforce — New Lead**
```
Trigger: New Lead
Salesforce Account: [Connected]
```

### Record Updated

**Google Sheets — Updated Row**
```
Trigger: New or Updated Spreadsheet Row
Spreadsheet: [Your Sheet]
Worksheet: [Sheet1]
Trigger Column: [Column to watch]
```

**Airtable — Record Updated**
```
Trigger: New or Updated Record
Base: [Your Base]
Table: [Your Table]
```

### Form Submissions

**Typeform — New Entry**
```
Trigger: New Entry
Form: [Your Form]
```

**Google Forms — New Response**
```
Trigger: New Response in Spreadsheet
Spreadsheet: [Linked Sheet]
Worksheet: [Form Responses]
```

**JotForm — New Submission**
```
Trigger: New Submission
Form: [Your Form]
```

### Payments

**Stripe — New Payment** ⚡
```
Trigger: New Payment
Stripe Account: [Connected]
```

**PayPal — New Sale** ⚡
```
Trigger: Successful Sale
PayPal Account: [Connected]
```

### Communication

**Email — New Email**
```
Trigger: New Email
Label/Folder: [Optional]
```

**Slack — New Message** ⚡
```
Trigger: New Message Posted to Channel
Channel: [#channel-name]
```

**Gmail — New Email**
```
Trigger: New Email
Label: [Optional]
Search: [is:unread from:important@domain.com]
```

## Schedule Trigger

### Every Day
```
Trigger: Schedule by Zapier
Trigger Event: Every Day
Time of Day: 9:00 AM
Timezone: America/New_York
```

### Every Week
```
Trigger: Schedule by Zapier
Trigger Event: Every Week
Day of Week: Monday
Time of Day: 9:00 AM
```

### Every Month
```
Trigger: Schedule by Zapier
Trigger Event: Every Month
Day of Month: 1
Time of Day: 9:00 AM
```

### Custom Interval
```
Trigger: Schedule by Zapier
Trigger Event: Every Hour
```

Options: Every Hour, Every Day, Every Week, Every Month

## Catch Hook (Incoming Webhook)

Receive data from any system that can send HTTP requests.

### Setup
```
Trigger: Webhooks by Zapier
Trigger Event: Catch Hook
```

Zapier provides URL like:
```
https://hooks.zapier.com/hooks/catch/123456/abcdef/
```

### Send Test Data
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "amount": 99.99
  }' \
  "https://hooks.zapier.com/hooks/catch/123456/abcdef/"
```

### With Query Parameters
```bash
curl -X POST \
  "https://hooks.zapier.com/hooks/catch/123456/abcdef/?source=website&campaign=summer"
```

### Form Data
```bash
curl -X POST \
  -d "name=John Doe&email=john@example.com" \
  "https://hooks.zapier.com/hooks/catch/123456/abcdef/"
```

## Catch Raw Hook

For custom payload parsing (XML, CSV, non-standard JSON).

```
Trigger: Webhooks by Zapier
Trigger Event: Catch Raw Hook
```

Returns raw body as string. Use Formatter to parse.

## Retrieve Poll

Fetch data from any URL on a schedule.

```
Trigger: Webhooks by Zapier
Trigger Event: Retrieve Poll
URL: https://api.example.com/data
Headers: Authorization: Bearer xxx
```

Zapier polls the URL every 1-15 minutes.

## RSS Trigger

Monitor RSS feeds for new items.

```
Trigger: RSS by Zapier
Feed URL: https://blog.example.com/feed.xml
```

- Checks every 5-15 minutes
- Triggers on new items only
- Good for blog monitoring, news alerts

## Trigger Data Structure

Every trigger provides data you can use in subsequent steps:

### Example: New Stripe Payment
```json
{
  "id": "ch_123",
  "amount": 9900,
  "currency": "usd",
  "customer": "cus_abc",
  "customer_email": "john@example.com",
  "description": "Pro Plan",
  "status": "succeeded",
  "created": "2024-01-15T10:30:00Z"
}
```

### Example: New Google Sheets Row
```json
{
  "row_number": 42,
  "A": "John Doe",
  "B": "john@example.com",
  "C": "2024-01-15",
  "spreadsheet_id": "1abc...",
  "worksheet_id": "Sheet1"
}
```

## Deduplication

Zapier tracks which records have already triggered to avoid duplicates.

**Dedupe Key** — Unique identifier for each record:
- Google Sheets: Row number
- Airtable: Record ID
- Stripe: Payment ID

**Important:** If you delete and re-add a row with same data, it WILL trigger again (different row number).

## Trigger Best Practices

1. **Test with sample data** — Always test before enabling
2. **Use instant when available** — ⚡ triggers are faster and more reliable
3. **Add filters after trigger** — Don't process unwanted records
4. **Watch for trigger loops** — Trigger from same app you write to can loop
5. **Consider rate limits** — High-volume triggers can burn tasks quickly
