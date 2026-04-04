# Zapier Tables — No-Code Database

## Overview

Zapier Tables is a built-in database for storing and managing data without external tools.

| Feature | Description |
|---------|-------------|
| **Records** | Row-based data storage |
| **Fields** | Typed columns (text, number, date, etc.) |
| **Views** | Filtered/sorted perspectives |
| **Automations** | Native Zap triggers/actions |
| **API** | REST API for external access |

## Create Table

### Via Zapier UI
1. Go to tables.zapier.com
2. Click "Create Table"
3. Define fields and types
4. Import existing data (optional)

### Field Types

| Type | Description | Example |
|------|-------------|---------|
| Text | Single line | Name, Email |
| Long Text | Multi-line | Description, Notes |
| Number | Numeric | Amount, Quantity |
| Date | Date/time | Created At |
| Checkbox | Boolean | Is Active |
| Email | Email validation | Contact Email |
| URL | URL validation | Website |
| Phone | Phone validation | Contact Phone |
| Dropdown | Select from options | Status: Draft/Active/Done |
| Linked Record | Reference another table | Customer → Orders |
| Attachment | File upload | Invoice PDF |
| Button | Trigger automation | "Process" button |
| AI Field | Auto-generated | Sentiment, Summary |

## Tables API

### Authentication

```bash
export ZAPIER_TABLES_TOKEN="your_tables_api_token"
```

Get token from: Tables → Settings → API

### List Records

```bash
curl -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records"
```

### Get Single Record

```bash
curl -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records/RECORD_ID"
```

### Create Record

```bash
curl -X POST \
  -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "Name": "John Doe",
      "Email": "john@example.com",
      "Status": "Active",
      "Amount": 99.99
    }
  }' \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records"
```

### Update Record

```bash
curl -X PATCH \
  -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "Status": "Completed",
      "Processed At": "2024-01-15T10:30:00Z"
    }
  }' \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records/RECORD_ID"
```

### Delete Record

```bash
curl -X DELETE \
  -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records/RECORD_ID"
```

### Filter Records

```bash
curl -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records?filter=Status%3DActive"
```

### Sort Records

```bash
curl -H "Authorization: Bearer $ZAPIER_TABLES_TOKEN" \
  "https://tables.zapier.com/api/v1/tables/TABLE_ID/records?sort=-Created%20At"
```

## Zap Integration

### Trigger: New Record

```
Trigger: Zapier Tables
Event: New Record
Table: [Your Table]
View: [Optional - only trigger for records in view]
```

### Trigger: Updated Record

```
Trigger: Zapier Tables
Event: Updated Record
Table: [Your Table]
```

### Action: Create Record

```
Action: Zapier Tables
Event: Create Record
Table: Contacts
Fields:
  Name: {{trigger.name}}
  Email: {{trigger.email}}
  Status: New
  Created At: {{zap_meta_human_now}}
```

### Action: Update Record

```
Action: Zapier Tables
Event: Update Record
Table: Contacts
Record: {{find_step.id}}
Fields:
  Status: Processed
  Processed At: {{zap_meta_human_now}}
```

### Action: Find Record

```
Action: Zapier Tables
Event: Find Record
Table: Contacts
Field: Email
Value: {{trigger.email}}
```

### Action: Find or Create

```
Action: Zapier Tables
Event: Find or Create Record
Table: Contacts
Search Field: Email
Search Value: {{trigger.email}}
-- If not found, create with: --
Name: {{trigger.name}}
Email: {{trigger.email}}
Status: New
```

## Button Fields

Buttons trigger Zaps when clicked.

### Setup
1. Add Button field to table
2. Create Zap with trigger: "Button Clicked in Table"
3. Button automatically links to Zap

### Example: Approve Record
```
Button: "Approve"
↓
Trigger: Button Clicked
→ Update Record: Status = "Approved"
→ Send Email: "Your request was approved"
```

## AI Fields

Auto-generate content using AI.

### Sentiment Analysis
```
Field: Sentiment (AI)
Source: Feedback field
Output: Positive/Negative/Neutral
```

### Summarization
```
Field: Summary (AI)
Source: Long Text field
Output: 2-3 sentence summary
```

### Categorization
```
Field: Category (AI)
Source: Description field
Categories: Bug, Feature Request, Question, Other
```

## Linked Records

Create relationships between tables.

### One-to-Many
```
Customers Table:
  - ID
  - Name
  - Email

Orders Table:
  - ID
  - Customer (Linked to Customers)
  - Total
  - Date
```

### Access Linked Data
In Zap:
```
{{trigger.Customer.Name}}
{{trigger.Customer.Email}}
```

## Views

Save filtered/sorted perspectives.

### Create View
1. Apply filters and sorts
2. Click "Save as View"
3. Name the view

### Use in Zaps
```
Trigger: New Record in View
Table: Orders
View: "Pending Orders"
```

Only triggers for records matching view criteria.

## Import/Export

### Import CSV
```
Tables → Import → Upload CSV
Map columns to fields
Review and confirm
```

### Export Data
```
Tables → Export → CSV
Download all records
```

### Sync with Google Sheets
Use Zap:
```
Trigger: New Row in Google Sheets
→ Create Record in Zapier Table

Trigger: New Record in Zapier Table
→ Create Row in Google Sheets
```

## Common Patterns

### CRM in Tables

```
Contacts Table:
  - Name (Text)
  - Email (Email)
  - Company (Text)
  - Status (Dropdown: Lead/Customer/Churned)
  - Last Contact (Date)
  - Notes (Long Text)
  - Follow Up (Button → triggers reminder Zap)
```

### Order Management

```
Orders Table:
  - Order ID (Number)
  - Customer (Linked to Contacts)
  - Items (Long Text)
  - Total (Number)
  - Status (Dropdown: Pending/Processing/Shipped/Delivered)
  - Process (Button → triggers fulfillment Zap)

Views:
  - Pending Orders (Status = Pending)
  - Today's Shipments (Status = Processing)
```

### Task Tracker

```
Tasks Table:
  - Title (Text)
  - Description (Long Text)
  - Assignee (Dropdown)
  - Due Date (Date)
  - Priority (Dropdown: Low/Medium/High)
  - Status (Dropdown: To Do/In Progress/Done)
  - Complete (Button → marks done + notifies)
```

## Best Practices

1. **Use appropriate field types** — Validates data automatically
2. **Create views for Zap triggers** — Filter at source, not in Zap
3. **Link tables** — Avoid data duplication
4. **Use buttons for actions** — One-click automation
5. **AI fields for enrichment** — Auto-categorize, summarize
