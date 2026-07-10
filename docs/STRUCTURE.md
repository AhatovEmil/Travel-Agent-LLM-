# Project Structure — Travel Agent

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py          # User, Trip, Artifact
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── deps.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   └── trips.py
│   │   └── services/
│   │       ├── engine.py      # TravelEngine (DeepSeek)
│   │       └── pipeline.py    # 4 фазы
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   └── pages/
│   │       ├── Auth.jsx
│   │       ├── Dashboard.jsx
│   │       └── Trip.jsx
│   └── ...
├── docs/
├── docker-compose.yml
└── README.md
```
