# Database Schema — Travel Agent

## users

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| email | VARCHAR(255) | UNIQUE, NOT NULL |
| password_hash | VARCHAR(512) | NOT NULL |
| created_at | TIMESTAMP TZ | DEFAULT now |

## trips

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| owner_id | INTEGER | FK → users.id |
| name | VARCHAR(255) | NOT NULL |
| brief | TEXT | описание поездки от пользователя |
| status | VARCHAR(32) | draft / running / completed / failed |
| current_phase | VARCHAR(32) | brief / itinerary / budget / checklist |
| error | TEXT | текст ошибки |
| created_at, updated_at | TIMESTAMP TZ | |

## artifacts

| Колонка | Тип | Ограничения |
|---|---|---|
| id | INTEGER | PK |
| trip_id | INTEGER | FK → trips.id |
| phase | VARCHAR(32) | brief / itinerary / budget / checklist |
| title | VARCHAR(255) | |
| content | TEXT | markdown от LLM |
| created_at | TIMESTAMP TZ | |
