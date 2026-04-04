# Common Zapier Patterns

## Form → Database → Notification

**Use case:** Capture leads, notify team

```
Trigger: Typeform → New Entry
↓
Action 1: Find or Create HubSpot Contact
  Search: email
  Create if not found
↓
Action 2: Create Google Sheets Row
  Log all submissions
↓
Action 3: Send Slack Message
  Channel: #leads
  Message: "New lead: {{name}} from {{company}}"
↓
Action 4: Send Gmail
  To: {{trigger.email}}
  Subject: Thanks for reaching out!
```

## Payment → Fulfillment → Communication

**Use case:** E-commerce order flow

```
Trigger: Stripe → New Payment ⚡
↓
Filter: Amount greater than 0
↓
Action 1: Create Airtable Record
  Table: Orders
  Status: Pending
↓
Action 2: Send Gmail
  Order confirmation
↓
Action 3: Send Twilio SMS
  "Order confirmed! We'll notify when shipped."
↓
Action 4: Create Trello Card
  List: To Fulfill
```

## CRM Sync (Bidirectional)

**Use case:** Keep systems in sync

```
Zap A: Salesforce → HubSpot
  Trigger: New/Updated Salesforce Contact
  Action: Find or Create HubSpot Contact
  
Zap B: HubSpot → Salesforce  
  Trigger: New/Updated HubSpot Contact
  Action: Find or Create Salesforce Contact
  
⚠️ Add filter to prevent loops:
  Only continue if "Last Modified By" ≠ "Zapier"
```

## Scheduled Report

**Use case:** Daily/weekly summaries

```
Trigger: Schedule → Every Monday at 9 AM
↓
Action 1: Find Airtable Records
  Filter: Created This Week
↓
Action 2: Formatter → Spreadsheet Formula
  Calculate totals
↓  
Action 3: Send Email
  Weekly summary with stats
```

## Multi-Channel Content Distribution

**Use case:** Publish once, distribute everywhere

```
Trigger: WordPress → New Post Published
↓
Path A: Social Media
  → Create Twitter Thread
  → Post to LinkedIn
  → Create Facebook Post
  
Path B: Email
  → Add to Mailchimp Campaign Draft
  
Path C: Team
  → Send Slack Message to #marketing
```

## Approval Workflow

**Use case:** Manager approval required

```
Trigger: Form Submission (expense request)
↓
Action 1: Create Zapier Tables Record
  Status: Pending Approval
↓
Action 2: Send Slack to Manager
  Include Approve/Reject buttons (via Block Kit)
↓
Zap B: Slack Reaction Added ⚡
  If reaction = ✅
    → Update status to Approved
    → Process expense
    → Notify requester
  If reaction = ❌
    → Update status to Rejected
    → Notify requester with reason
```

## Error Handling Pattern

**Use case:** Graceful failure recovery

```
Trigger: Any
↓
Action 1: API Call (might fail)
  ☑️ Continue on error
↓
Path A: Success
  Condition: Response status = 200
  → Continue normal flow
  
Path B: Failure
  Condition: Response status ≠ 200
  → Log to Error Sheet
  → Send Slack Alert
  → Create follow-up task
```

## Deduplication Pattern

**Use case:** Prevent duplicate processing

```
Trigger: New Record
↓
Action 1: Find Record in Processed Table
  Search by unique ID
↓
Filter: Only continue if NOT found
↓
Action 2: Process the record
↓
Action 3: Add to Processed Table
  Store unique ID + timestamp
```

## Webhook Chain Pattern

**Use case:** Complex multi-stage processing

```
Zap A: Receive & Validate
  Trigger: Catch Hook
  → Validate data
  → POST to Zap B webhook

Zap B: Process & Enrich
  Trigger: Catch Hook (from Zap A)
  → API calls for enrichment
  → POST to Zap C webhook
  
Zap C: Store & Notify
  Trigger: Catch Hook (from Zap B)
  → Save to database
  → Send notifications
```

## Batch Processing Pattern

**Use case:** Aggregate items before processing

```
Zap A: Collect Items
  Trigger: Each new order
  → Add to Digest
  
Zap B: Process Batch
  Trigger: Schedule (daily at 6 PM)
  → Release Digest
  → Process all items together
  → Send single summary report
```

## Customer Health Monitoring

**Use case:** Proactive churn prevention

```
Trigger: Schedule → Daily
↓
Action 1: Find Airtable Records
  Filter: Last Activity > 30 days ago
↓
Loop: For each inactive customer
  → Check usage data
  → If usage < threshold:
    → Add to "At Risk" segment
    → Send re-engagement email
    → Create task for account manager
```

## Lead Scoring Pattern

**Use case:** Prioritize leads by engagement

```
Trigger: Any lead activity (email open, page visit, etc.)
↓
Action 1: Find Lead Record
↓
Action 2: Code (calculate score)
  score = currentScore
  if (activity == 'email_open') score += 5
  if (activity == 'demo_request') score += 50
  if (activity == 'pricing_page') score += 20
↓
Action 3: Update Lead Score
↓
Filter: If score > 100
  → Alert Sales Team
  → Move to "Hot Leads"
```

## Data Transformation Pattern

**Use case:** Clean and format data

```
Trigger: New messy data
↓
Formatter: Lowercase email
Formatter: Capitalize name
Formatter: Extract domain from email
Formatter: Parse date to standard format
Formatter: Calculate values
↓
Action: Store clean data
```

## Multi-Tenant Pattern

**Use case:** Different flows per customer

```
Trigger: New Event
↓
Lookup: Customer Settings Table
  Find by customer_id
↓
Path A: Customer uses Slack
  → Send to their Slack workspace
  
Path B: Customer uses Email
  → Send to their email
  
Path C: Customer uses Webhook
  → POST to their endpoint
```
