# Telegram Messaging Service

A lightweight asynchronous messaging service built with **FastAPI** for sending, editing, deleting, and recreating Telegram bot messages.

The service is designed to work alongside a Django-based backend. Django manages users, bots, channels, message state, and business logic, while this service is responsible for executing Telegram operations asynchronously.

---

## Features

* Send Telegram messages
* Edit existing Telegram messages
* Delete Telegram messages
* Recreate messages by deleting the old message and sending a new one
* Asynchronous message processing
* `asyncio.Queue` based job queue
* Multiple asynchronous workers
* Batch message submission
* Batch result aggregation
* Support for Telegram inline keyboards
* Docker support
* FastAPI OpenAPI documentation

---

## Architecture

The service follows a simple asynchronous architecture:

```text
Django
   │
   │ HTTP Request
   ▼
FastAPI
   │
   ▼
Message Queue
   │
   ├── Worker 1
   ├── Worker 2
   └── Worker 3
   │
   ▼
Telegram Bot API
   │
   ▼
Batch Results
   │
   │ HTTP Request
   ▼
Django
```

Django is responsible for business decisions, such as determining whether a message should be edited or recreated.

FastAPI is responsible for executing Telegram operations and collecting their results.

---

## Message Operations

Each message contains an `action` field:

```text
new
edit
recreate
```

### New

Sends a new Telegram message.

```json
{
    "message_id": null,
    "action": "new"
}
```

### Edit

Edits an existing Telegram message.

```json
{
    "message_id": "501",
    "action": "edit"
}
```

### Recreate

Deletes the existing message and sends a new one.

```json
{
    "message_id": "501",
    "action": "recreate"
}
```

The newly created Telegram message ID is returned to Django so it can update its stored message ID.

---

## Project Structure

```text
app/
├── main.py
│
├── core/
│   ├── __init__.py
│   └── config.py
│
├── api/
│   ├── __init__.py
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       └── telegram.py
│
├── schemas/
│   └── telegram.py
│
├── services/
│   └── telegram/
│       ├── __init__.py
│       ├── service.py
│       ├── sender.py
│       └── markup.py
│
└── workers/
    ├── queue.py
    ├── batch_manager.py
    └── message_worker.py
```

---

## Requirements

* Python 3.12+
* FastAPI
* Uvicorn
* Gunicorn
* python-telegram-bot
* Pydantic Settings

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Environment Variables

Create a `.env` file for local development:

```env
APP_NAME=Telegram Service
DEBUG=false

TELEGRAM_PROXY_URL=

QUEUE_MAX_SIZE=1000
WORKER_COUNT=3

SERVICE_ID=
SERVICE_SECRET=
```

### Configuration

| Variable             | Description                            |
| -------------------- | -------------------------------------- |
| `APP_NAME`           | Application name                       |
| `DEBUG`              | Enables debug mode                     |
| `TELEGRAM_PROXY_URL` | Optional Telegram proxy                |
| `QUEUE_MAX_SIZE`     | Maximum queue size                     |
| `WORKER_COUNT`       | Number of async message workers        |
| `SERVICE_ID`         | Internal service authentication ID     |
| `SERVICE_SECRET`     | Internal service authentication secret |

User-specific Telegram bot tokens are **not** stored in the service configuration. They are provided by Django as part of each message request.

---

## Running Locally

Start the development server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
/docs
```

Alternative documentation:

```text
/redoc
```

---

## Production

The service is designed to run with Gunicorn and Uvicorn workers.

```bash
gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 1
```

### Why one Gunicorn worker?

The current queue implementation uses:

```python
asyncio.Queue
```

The queue exists in process memory.

Therefore, multiple Gunicorn processes would create independent queues:

```text
Process 1 → Queue 1
Process 2 → Queue 2
Process 3 → Queue 3
```

For the current architecture, a single process is intentional.

If the service later needs multiple instances or processes, the queue and batch state can be moved to a shared system such as Redis.

---

## Docker

Build the image:

```bash
docker build -t telegram-service .
```

Run the container:

```bash
docker run \
    --env-file .env \
    -p 8000:8000 \
    telegram-service
```

The Docker container runs:

```text
Gunicorn
   ↓
Uvicorn Worker
   ↓
FastAPI
   ↓
Async Message Workers
```

---

## API

Base URL:

```text
/api/v1
```

### Send Message

```http
POST /api/v1/telegram/send-message
```

Example:

```json
{
    "id": 1,
    "token": "BOT_TOKEN",
    "chat_id": -100123456789,
    "message_id": null,
    "text": "USDT: 1045000",
    "reply_markup": null,
    "action": "new"
}
```

---

### Edit Message

```json
{
    "id": 1,
    "token": "BOT_TOKEN",
    "chat_id": -100123456789,
    "message_id": "501",
    "text": "USDT: 1047000",
    "reply_markup": null,
    "action": "edit"
}
```

---

### Recreate Message

```json
{
    "id": 1,
    "token": "BOT_TOKEN",
    "chat_id": -100123456789,
    "message_id": "501",
    "text": "USDT: 1047000",
    "reply_markup": null,
    "action": "recreate"
}
```

The service deletes message `501`, sends a new message, and returns the new Telegram message ID.

---

## Batch Processing

The recommended way to send many messages is the batch endpoint:

```http
POST /api/v1/telegram/send-batch
```

Example:

```json
{
    "batch_id": "batch-001",
    "messages": [
        {
            "id": 1,
            "token": "BOT_TOKEN",
            "chat_id": -100111111111,
            "message_id": "501",
            "text": "USDT: 1045000",
            "reply_markup": null,
            "action": "edit"
        },
        {
            "id": 2,
            "token": "BOT_TOKEN",
            "chat_id": -100222222222,
            "message_id": "700",
            "text": "USDT: 1045000",
            "reply_markup": null,
            "action": "recreate"
        }
    ]
}
```

The API accepts the batch immediately:

```json
{
    "status": "accepted",
    "batch_id": "batch-001",
    "count": 2
}
```

Messages are then placed into the asynchronous queue.

Workers process the queue concurrently.

---

## Batch Processing Flow

```text
Django
   │
   │ Send one batch request
   ▼
FastAPI
   │
   ├── Message 1
   ├── Message 2
   ├── Message 3
   └── ...
   │
   ▼
asyncio.Queue
   │
   ├── Worker 1
   ├── Worker 2
   └── Worker 3
   │
   ▼
Telegram
   │
   ▼
Result Collector
   │
   ▼
One aggregated result
   │
   ▼
Django
```

This prevents Django from having to wait for every Telegram API request individually.

---

## Result Format

Each processed message produces a result.

Successful edit:

```json
{
    "id": 1,
    "chat_id": -100111111111,
    "message_id": "501",
    "status": "edited",
    "worker": 0
}
```

Successful new message:

```json
{
    "id": 1,
    "chat_id": -100111111111,
    "message_id": "502",
    "status": "sent",
    "worker": 1
}
```

Failed message:

```json
{
    "id": 1,
    "chat_id": -100111111111,
    "message_id": "501",
    "status": "failed",
    "error": "Message to edit not found",
    "worker": 0
}
```

The `id` field is the original Django-side identifier and allows Django to map the result back to the correct channel or message record.

---

## Reply Markup

Telegram inline keyboards can be passed through the `reply_markup` field.

Example:

```json
{
    "reply_markup": [
        [
            {
                "text": "Buy",
                "callback_data": "buy"
            },
            {
                "text": "Sell",
                "callback_data": "sell"
            }
        ]
    ]
}
```

The service converts this structure into Telegram's `InlineKeyboardMarkup`.

---

## Responsibilities

### Django

Django owns:

* Users
* Telegram bots
* Channels and groups
* Telegram chat IDs
* Stored message IDs
* Reply markup/configuration
* Business logic
* Scheduling
* Deciding `new`, `edit`, or `recreate`
* Persisting final results

### FastAPI

FastAPI owns:

* Telegram API communication
* Message queue
* Async workers
* Sending messages
* Editing messages
* Deleting messages
* Recreating messages
* Per-message delivery results
* Batch result aggregation

This separation keeps business logic in Django and Telegram delivery logic in the messaging service.

---

## Scaling

The current service uses an in-memory queue:

```python
asyncio.Queue
```

This is intentionally simple and suitable for the current deployment.

For higher scale or multiple service instances, the architecture can later be extended to:

```text
Django
   │
   ▼
Redis
   │
   ├── FastAPI Instance 1
   ├── FastAPI Instance 2
   └── FastAPI Instance 3
```

At that point, queue state and batch state should be moved from process memory to Redis or another shared backend.

---

## Security

The Telegram service is intended to be accessed by trusted backend services rather than directly by public clients.

The service should use service-to-service authentication such as:

```text
X-Service-ID
X-Timestamp
X-Nonce
X-Signature
```

Telegram bot tokens should never be exposed to frontend clients.

Environment files containing secrets should not be committed to Git.

---

## Logging

The application writes logs to standard output so Docker and the hosting platform can collect them.

For production deployments, container logs can be collected by the host logging system or centralized logging infrastructure.

---

## License

Private project. All rights reserved.
