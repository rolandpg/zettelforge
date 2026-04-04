# Actions — Zapier

## Action Types

| Type | Purpose | Example |
|------|---------|---------|
| **Create** | Add new record | Create row, Create contact |
| **Update** | Modify existing | Update row, Update deal |
| **Find** | Search records | Find customer, Lookup row |
| **Find or Create** | Search, create if missing | Get or create contact |
| **Delete** | Remove record | Delete row |
| **Custom** | App-specific | Send email, Post message |

## Create Actions

### Create Google Sheets Row
```
Action: Create Spreadsheet Row
Spreadsheet: [Your Sheet]
Worksheet: [Sheet1]
Name: {{trigger.name}}
Email: {{trigger.email}}
Date: {{trigger.created_at}}
```

### Create Airtable Record
```
Action: Create Record
Base: [Your Base]
Table: [Contacts]
Name: {{trigger.name}}
Email: {{trigger.email}}
Status: New
```

### Create Salesforce Lead
```
Action: Create Lead
First Name: {{trigger.first_name}}
Last Name: {{trigger.last_name}}
Email: {{trigger.email}}
Company: {{trigger.company}}
Lead Source: Website
```

### Create Notion Database Item
```
Action: Create Database Item
Database: [Your Database]
Name: {{trigger.title}}
Status: To Do
Date: {{trigger.date}}
```

## Update Actions

### Update Google Sheets Row
```
Action: Update Spreadsheet Row
Spreadsheet: [Your Sheet]
Worksheet: [Sheet1]
Row: {{previous_step.row_number}}
Status: Processed
Processed Date: {{zap_meta_human_now}}
```

### Update Airtable Record
```
Action: Update Record
Base: [Your Base]
Table: [Contacts]
Record: {{find_step.id}}
Status: Active
Last Contact: {{zap_meta_human_now}}
```

### Update Salesforce Record
```
Action: Update Record
Object Type: Lead
Record: {{find_step.id}}
Status: Qualified
```

## Find Actions

### Find Google Sheets Row
```
Action: Lookup Spreadsheet Row
Spreadsheet: [Your Sheet]
Worksheet: [Sheet1]
Lookup Column: Email
Lookup Value: {{trigger.email}}
```

### Find Airtable Record
```
Action: Find Record
Base: [Your Base]
Table: [Contacts]
Field: Email
Search Value: {{trigger.email}}
```

### Find Salesforce Record
```
Action: Find Record
Object Type: Contact
Field to Search: Email
Search Value: {{trigger.email}}
```

## Find or Create Pattern

**Most reliable for syncing systems.** Searches first, creates only if not found.

### Airtable — Find or Create
```
Action: Find or Create Record
Base: [Your Base]
Table: [Contacts]
Search Field: Email
Search Value: {{trigger.email}}
-- If not found, create with: --
Name: {{trigger.name}}
Email: {{trigger.email}}
Source: Zapier
```

### HubSpot — Find or Create Contact
```
Action: Find or Create Contact
Search Property: email
Search Value: {{trigger.email}}
-- If not found, create with: --
Email: {{trigger.email}}
First Name: {{trigger.first_name}}
Last Name: {{trigger.last_name}}
```

## Communication Actions

### Send Email (Gmail)
```
Action: Send Email
To: {{trigger.email}}
From Name: Your Company
Subject: Welcome to {{company_name}}
Body: Hi {{trigger.name}},

Thank you for signing up!

Best,
Team
```

### Send Slack Message
```
Action: Send Channel Message
Channel: #notifications
Message: New signup: {{trigger.name}} ({{trigger.email}})
```

### Send Slack Direct Message
```
Action: Send Direct Message
User: @john
Message: New lead assigned to you: {{trigger.name}}
```

### Send SMS (Twilio)
```
Action: Send SMS
To: {{trigger.phone}}
From: +1234567890
Body: Your order {{trigger.order_id}} has shipped!
```

## Webhook Action

Send data to any URL.

### POST JSON
```
Action: Webhooks by Zapier → POST
URL: https://api.yourapp.com/webhook
Payload Type: JSON
Data:
  name: {{trigger.name}}
  email: {{trigger.email}}
  event: new_signup
```

### POST with Headers
```
Action: Webhooks by Zapier → POST
URL: https://api.yourapp.com/webhook
Headers:
  Authorization: Bearer your_api_key
  Content-Type: application/json
Data:
  user_id: {{trigger.id}}
```

### Custom Request
```
Action: Webhooks by Zapier → Custom Request
Method: PATCH
URL: https://api.yourapp.com/users/{{trigger.user_id}}
Headers:
  Authorization: Bearer your_api_key
Data:
  status: active
```

## Code Actions (JavaScript/Python)

### JavaScript
```javascript
// Input: inputData.email, inputData.name
const email = inputData.email.toLowerCase().trim();
const domain = email.split('@')[1];
const isBusinessEmail = !['gmail.com', 'yahoo.com', 'hotmail.com'].includes(domain);

output = [{
  email: email,
  domain: domain,
  isBusinessEmail: isBusinessEmail,
  nameParts: inputData.name.split(' ')
}];
```

### Python
```python
# Input: input_data['email'], input_data['name']
email = input_data['email'].lower().strip()
domain = email.split('@')[1]
personal_domains = ['gmail.com', 'yahoo.com', 'hotmail.com']
is_business = domain not in personal_domains

output = [{
    'email': email,
    'domain': domain,
    'is_business_email': is_business,
    'first_name': input_data['name'].split()[0]
}]
```

## Delay Actions

### Delay For
```
Action: Delay by Zapier
Delay For: 1 hour
```

Options: minutes, hours, days

### Delay Until
```
Action: Delay by Zapier
Delay Until: {{trigger.event_date}}
Time: 9:00 AM
Timezone: America/New_York
```

### Delay for Business Hours
```
Action: Delay by Zapier
Resume at: Next weekday at 9:00 AM
```

## Looping

Process multiple items from a single trigger.

### Line Items
When trigger returns array (e.g., order items):
```
Action: Looping by Zapier
Values to Loop: {{trigger.line_items}}
-- For each item: --
Create Google Sheets Row:
  Product: {{loop.product_name}}
  Quantity: {{loop.quantity}}
  Price: {{loop.price}}
```

## Error Handling

### Continue on Error
```
Action Settings:
☑️ Continue Zap even if this action fails
```

### Paths for Error Handling
```
Path A: Success
  Condition: {{previous_step.id}} exists
  Action: Send success notification

Path B: Failure  
  Condition: {{previous_step.id}} doesn't exist
  Action: Send error alert
```

## Action Best Practices

1. **Test each action** — Verify data flows correctly
2. **Use Find or Create** — Prevents duplicates
3. **Add delays wisely** — Don't spam external APIs
4. **Handle errors** — Add paths for failure cases
5. **Check task usage** — Each action = 1 task minimum
