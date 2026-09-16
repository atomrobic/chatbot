# chatbot

A real-time Omegle-style Stranger Chat application built with Django Channels, Redis (or InMemoryChannelLayer for dev), and vanilla HTML/CSS/JS.

## Setup

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install django channels daphne channels-redis
```

Run the server:
```bash
python manage.py runserver
```
