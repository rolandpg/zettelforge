# Filters, Paths & Formatters — Zapier

## Filters

Filters stop the Zap if conditions aren't met. **Filters don't count as tasks.**

### Basic Filter Syntax

```
Only continue if...
[Field] [Condition] [Value]
```

### Text Conditions

| Condition | Example |
|-----------|---------|
| (Text) Contains | Email contains "@company.com" |
| (Text) Does not contain | Email does not contain "@test.com" |
| (Text) Exactly matches | Status exactly matches "approved" |
| (Text) Does not exactly match | Status does not match "spam" |
| (Text) Is in | Country is in "US, CA, UK" |
| (Text) Starts with | Name starts with "VIP" |
| (Text) Ends with | Email ends with ".edu" |
| (Text) Matches pattern | Phone matches "+1[0-9]{10}" |

### Number Conditions

| Condition | Example |
|-----------|---------|
| (Number) Greater than | Amount greater than 100 |
| (Number) Less than | Quantity less than 0 |
| (Number) Equals | Status code equals 200 |

### Boolean Conditions

| Condition | Example |
|-----------|---------|
| (Boolean) Is true | Is premium is true |
| (Boolean) Is false | Unsubscribed is false |

### Existence Conditions

| Condition | Example |
|-----------|---------|
| Exists | Email exists |
| Does not exist | Phone does not exist |

### Date Conditions

| Condition | Example |
|-----------|---------|
| (Date/Time) After | Created after 2024-01-01 |
| (Date/Time) Before | Expires before today |

### Multiple Conditions (AND)

All conditions must be true:
```
Only continue if...
☑️ AND
  Status exactly matches "paid"
  Amount greater than 50
  Country is in "US, CA"
```

### Multiple Conditions (OR)

Any condition can be true:
```
Only continue if...
☑️ OR
  Email ends with "@company.com"
  Is VIP is true
  Amount greater than 1000
```

### Combining AND/OR

```
Only continue if...
☑️ AND
  Status exactly matches "paid"
  ☑️ OR
    Country is in "US, CA"
    Is VIP is true
```

## Paths

Paths create conditional branches. Each path runs its own set of actions.

### Basic Path Structure

```
Trigger
↓
Path A: High Value
  Condition: Amount > 1000
  → Send to Sales Team
  → Create VIP Flag

Path B: Standard
  Condition: Amount <= 1000
  → Add to Newsletter
  → Send Welcome Email

Path C: (Fallback)
  Condition: Always run
  → Log to Spreadsheet
```

### Path Conditions

Same conditions as filters. Each path needs its condition.

### Path Examples

**Route by Country:**
```
Path A: US/Canada
  Condition: Country is in "US, CA"
  → Assign to NA Sales Team

Path B: Europe
  Condition: Country is in "UK, DE, FR, ES, IT"
  → Assign to EU Sales Team

Path C: Other
  → Assign to Global Team
```

**Route by Amount:**
```
Path A: Enterprise
  Condition: Amount greater than 10000
  → Create Salesforce Opportunity
  → Alert Sales Director

Path B: SMB
  Condition: Amount between 1000 and 10000
  → Add to HubSpot
  → Send SMB Sequence

Path C: Self-Serve
  → Add to Email List Only
```

**Success/Failure:**
```
Path A: Success
  Condition: {{api_response.status}} equals "success"
  → Update Record as Processed
  → Send Confirmation

Path B: Failure
  Condition: {{api_response.status}} does not equal "success"
  → Log Error to Sheet
  → Send Alert to Slack
```

## Formatters

Transform data between steps. **Formatters don't count as tasks.**

### Text Formatters

**Capitalize**
```
Input: john doe
Output: John Doe
```

**Lowercase**
```
Input: JOHN@EXAMPLE.COM
Output: john@example.com
```

**Uppercase**
```
Input: new york
Output: NEW YORK
```

**Trim Whitespace**
```
Input: "  john@example.com  "
Output: "john@example.com"
```

**Replace**
```
Input: +1-555-123-4567
Find: -
Replace: (empty)
Output: +15551234567
```

**Split Text**
```
Input: John Doe
Separator: (space)
Segment Index: 0
Output: John
```

**Extract Pattern (Regex)**
```
Input: "Order #12345 confirmed"
Pattern: #(\d+)
Output: 12345
```

**Truncate**
```
Input: "Very long text here..."
Max Length: 10
Append: ...
Output: "Very long..."
```

### Number Formatters

**Format Number**
```
Input: 1234.5
Format: $#,##0.00
Output: $1,234.50
```

**Math Operations**
```
Operation: Add
Numbers: {{amount}}, 10
Output: (amount + 10)
```

```
Operation: Multiply
Numbers: {{quantity}}, {{price}}
Output: (quantity × price)
```

**Round Number**
```
Input: 3.14159
Decimal Places: 2
Output: 3.14
```

**Spreadsheet-Style Formula**
```
Formula: ({{price}} * {{quantity}}) - {{discount}}
Output: Calculated total
```

### Date/Time Formatters

**Format Date**
```
Input: 2024-01-15T14:30:00Z
Format: MMM DD, YYYY
Output: Jan 15, 2024
```

**Common Date Formats:**
| Format | Output |
|--------|--------|
| `YYYY-MM-DD` | 2024-01-15 |
| `MM/DD/YYYY` | 01/15/2024 |
| `MMM DD, YYYY` | Jan 15, 2024 |
| `MMMM D, YYYY` | January 15, 2024 |
| `ddd, MMM D` | Mon, Jan 15 |

**Adjust Date**
```
Input: 2024-01-15
Operation: Add 7 days
Output: 2024-01-22
```

```
Input: 2024-01-15
Operation: Subtract 1 month
Output: 2023-12-15
```

**Compare Dates**
```
Input A: {{trigger.start_date}}
Input B: {{zap_meta_human_now}}
Output: "before", "after", or "same"
```

### Utilities

**Lookup Table**
```
Input: US
Table:
  US → United States
  CA → Canada
  UK → United Kingdom
Output: United States
```

**Default Value**
```
Input: {{trigger.phone}}
Default: Not provided
Output: (phone if exists, else "Not provided")
```

**Pick from List**
```
Input: {{trigger.items}}
Index: 0
Output: First item
```

**Line Itemizer**
Create multiple line items from delimited string:
```
Input: "apple,banana,cherry"
Separator: ,
Output: ["apple", "banana", "cherry"]
```

### Sub-Zap (Reusable Flows)

Create reusable Zap chunks:

```
Main Zap:
  Trigger → Data
  Call Sub-Zap:
    Input: {{trigger.data}}
    → Sub-Zap processes
    ← Returns result
  Use {{sub_zap.result}}
```

## Digest (Batch)

Collect items over time, then process as batch.

### Setup
```
Action: Digest by Zapier
Mode: Collect items
Release: Every day at 9:00 AM
```

### Example: Daily Summary
```
Every new order:
  → Add to digest: {{order_id}}, {{amount}}

Daily at 9am:
  → Release digest
  → Send email with all orders
```

### Digest Modes

| Mode | Behavior |
|------|----------|
| Append | Add to end |
| Prepend | Add to start |
| Replace | Overwrite if key matches |

## Best Practices

1. **Filter early** — Don't waste tasks on records you'll discard
2. **Use paths for branching** — Cleaner than multiple Zaps
3. **Format before actions** — Clean data before sending
4. **Test each formatter** — Verify output matches expectations
5. **Default values** — Handle missing data gracefully
