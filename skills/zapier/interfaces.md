# Zapier Interfaces — Forms, Pages & Chatbots

## Overview

Zapier Interfaces lets you create custom apps without code.

| Component | Purpose |
|-----------|---------|
| **Forms** | Collect data from users |
| **Pages** | Display data (dashboards, portals) |
| **Chatbots** | AI-powered conversation interfaces |
| **Kanban** | Visual task management |
| **Tables** | Data grids with editing |

## Forms

### Create Form

1. Go to interfaces.zapier.com
2. New Interface → Form
3. Add fields
4. Configure submissions

### Field Types

| Type | Use Case |
|------|----------|
| Short Text | Name, Title |
| Long Text | Description, Feedback |
| Email | Contact email |
| Number | Quantity, Amount |
| Dropdown | Select from options |
| Multiple Choice | Radio buttons |
| Checkboxes | Multi-select |
| Date | Event dates |
| Time | Appointment times |
| File Upload | Documents, images |
| Hidden | Pre-filled values |

### Form Settings

**Submission Behavior:**
```
On Submit:
  ☑️ Show success message
  ☑️ Redirect to URL
  ☑️ Allow another submission
```

**Pre-fill Values:**
```
URL: https://yourform.zapier.app?name=John&email=john@example.com
```

Fields auto-populate from URL parameters.

### Form to Zap

```
Trigger: New Submission in Zapier Interfaces
Interface: [Your Form]
↓
→ Create Record in Zapier Tables
→ Send Email Confirmation
→ Add to CRM
```

### Conditional Logic

Show/hide fields based on answers:
```
If "Plan" = "Enterprise"
  Show: "Company Size" field
  Show: "Budget" field
```

### File Uploads

```
Field: Resume Upload
Allowed Types: PDF, DOC, DOCX
Max Size: 10MB
```

Access in Zap: `{{trigger.Resume Upload.url}}`

## Pages

### Create Page

1. New Interface → Page
2. Add components
3. Connect data sources
4. Publish

### Page Components

| Component | Purpose |
|-----------|---------|
| **Text** | Headlines, descriptions |
| **Table** | Data grid from Tables |
| **Chart** | Bar, line, pie charts |
| **Kanban** | Task board |
| **Form** | Embedded form |
| **Button** | Trigger actions |
| **Image** | Logos, graphics |
| **Embed** | External content |

### Connect to Tables

```
Table Component:
  Source: Zapier Tables → Orders
  Columns: Order ID, Customer, Total, Status
  Filter: Status = "Pending"
  Sort: Created At (descending)
```

### Charts

```
Chart Component:
  Type: Bar Chart
  Source: Zapier Tables → Sales
  X-Axis: Month
  Y-Axis: Revenue (Sum)
```

### Dynamic Content

Use variables from Tables:
```
Text: "Total Orders: {{tables.orders.count}}"
Text: "Revenue: ${{tables.sales.total_sum}}"
```

### Page Actions

Buttons can trigger Zaps:
```
Button: "Approve All"
→ Trigger: Button Clicked
→ Update Records where Status = "Pending"
→ Set Status = "Approved"
```

## Chatbots

### Create Chatbot

1. New Interface → Chatbot
2. Configure AI settings
3. Define knowledge base
4. Set up actions

### AI Configuration

```
System Prompt:
"You are a helpful customer support agent for Acme Corp.
You can help with:
- Order status inquiries
- Return requests
- Product questions

Always be friendly and professional."
```

### Knowledge Base

Connect data sources the AI can reference:
- Zapier Tables
- Google Docs
- Notion pages
- PDF uploads

### Chatbot Actions

Let the bot trigger Zaps:
```
Action: "Create Support Ticket"
When user says: needs help, has issue, problem with
→ Trigger Zap: Create record in Support Table
→ Send notification to support team
```

### Variables in Chatbot

Pre-fill context:
```
URL: https://yourchatbot.zapier.app?customer_id=12345&name=John
```

Bot can access: `{{customer_id}}`, `{{name}}`

### Handoff to Human

```
If bot confidence < 70%:
  "Let me connect you with a human agent."
  → Trigger Zap: Create urgent ticket
  → Notify support channel
```

## Kanban Boards

### Setup

```
Kanban Component:
  Source: Zapier Tables → Tasks
  Group By: Status (To Do, In Progress, Done)
  Card Title: Task Name
  Card Details: Assignee, Due Date
```

### Drag-and-Drop

When card moves between columns:
- Record updates automatically
- Can trigger Zap on status change

### Example: Project Board

```
Columns:
  - Backlog
  - To Do
  - In Progress
  - Review
  - Done

Card Fields:
  - Title
  - Assignee
  - Priority (color coded)
  - Due Date
  - Tags
```

## Authentication

### Public Access
```
Sharing: Anyone with link
```

### Password Protection
```
Sharing: Password required
Password: ********
```

### Zapier Login
```
Sharing: Zapier account required
Allowed Users: specific emails or domains
```

### Custom Auth (via Zap)
```
Interface loads → Check auth cookie
If missing → Redirect to login form
Login form → Validate credentials via Zap
Success → Set cookie, redirect to interface
```

## Embedding

### Embed in Website

```html
<iframe 
  src="https://yourform.zapier.app" 
  width="100%" 
  height="600"
  frameborder="0">
</iframe>
```

### Embed in Notion

```
/embed → paste Interface URL
```

### Custom Domain

1. Interfaces → Settings → Custom Domain
2. Add CNAME record: `forms.yourcompany.com` → `zapier.app`
3. Verify and enable

## Styling

### Branding

```
Settings:
  Logo: Upload company logo
  Primary Color: #3B82F6
  Background: #FFFFFF
  Font: Inter
```

### Custom CSS (Advanced)

```css
/* Custom button style */
.zap-button-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
}
```

## Common Patterns

### Lead Capture Form

```
Form Fields:
  - Name (required)
  - Email (required)
  - Company
  - Phone
  - "How did you hear about us?" (dropdown)

On Submit:
  → Create CRM contact
  → Send welcome email
  → Notify sales team
```

### Customer Portal

```
Page Components:
  - Header with logo
  - "Your Orders" table (filtered by logged-in user)
  - "Submit Request" form
  - "Chat with Support" chatbot
```

### Internal Dashboard

```
Page Components:
  - KPI cards (Revenue, Users, Churn)
  - Revenue chart (monthly)
  - Recent orders table
  - Task kanban board
  - "Quick Actions" buttons
```

## Best Practices

1. **Mobile-first** — Test on mobile devices
2. **Progressive disclosure** — Don't overwhelm with fields
3. **Validation messages** — Clear error feedback
4. **Loading states** — Show progress for slow operations
5. **Success confirmation** — Confirm submissions clearly
