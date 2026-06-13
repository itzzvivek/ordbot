# OrdBot

### A WhatsApp chatbot that handles end-to-end food ordering — from collecting customer details to processing payments — built with Django, Twilio, and Razorpay.


## Features

- Guided conversation flow — collects name, address, phone step by step
- Dynamic menu from database — manage items via Django admin
- Multi-item ordering with quantities (`1x2, 3, 2x1`)
- Automatic order total calculation
- Razorpay payment link generation
- Automatic WhatsApp success message on payment (via Razorpay webhook)
- Order history and user sessions in PostgreSQL
- Docker + ngrok setup for local development

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1 |
| WhatsApp | Twilio API |
| Payments | Razorpay |
| Database | PostgreSQL (SQLite for local) |
| Tunneling | ngrok (static domain) |
| Container | Docker + Docker Compose |

---

### Prerequisites

- Docker & Docker Compose
- [Twilio account](https://twilio.com) with WhatsApp Sandbox enabled
- [Razorpay account](https://razorpay.com) (test mode works)
- [ngrok account](https://ngrok.com) with a free static domain

---

### 1. Clone the repo

```bash
git clone https://github.com/itzzvivek/Fitbot.git
cd Fitbot
```

### 2. Configure environment

```bash
cp .env.example .env
```

Fill in `.env`:

```env
SECRET_KEY=your-django-secret-key
DEBUG=True

# Database
DB_NAME=fitbot
DB_USER=fitbot
DB_PASSWORD=fitbot
DB_HOST=db

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER_FROM=+14155238886

# Razorpay
RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
RAZORPAY_KEY_SECRET=your_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# ngrok static domain (https://dashboard.ngrok.com/domains)
NGROK_AUTHTOKEN=your_ngrok_token
NGROK_URL=https://your-domain.ngrok-free.app
BASE_URL=https://your-domain.ngrok-free.app
```

### 3. Start with Docker

```bash
docker-compose up --build
```

This starts Django, PostgreSQL, and ngrok together. Migrations and menu seeding run automatically.

### 4. Set up Twilio WhatsApp Sandbox

1. Go to [Twilio Console → WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn)
2. Set **"When a message comes in"** to:

https://your-domain.ngrok-free.app/whatsapp/
3. Method: `POST` → Save
4. Send the sandbox join keyword from your WhatsApp to start testing

### 5. Set up Razorpay Webhook

1. Go to [Razorpay Dashboard → Settings → Webhooks](https://dashboard.razorpay.com/app/webhooks)
2. Click **Add New Webhook**
3. URL: `https://your-domain.ngrok-free.app/payment/webhook/`
4. Secret: same value as `RAZORPAY_WEBHOOK_SECRET` in `.env`


## Bot Commands

| Command | What it does |
|---|---|
| `hi` / `hello` | Start a new order |
| `menu` | Show the menu |
| `1, 2, 3` | Select items by number |
| `1x2, 3x1` | Select items with quantity |
| `confirm` | Proceed to payment |
| `cancel` | Cancel current order |
