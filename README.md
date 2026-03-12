# EMR-Lite
Система управления электронными медицинскими записями.

[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-33%20passed-brightgreen)]()
[![Coverage](https://img.shields.io/badge/Coverage-65%25-yellow)]()

---

## О проекте

**EMR-Lite** моделирует ключевые процессы медицинской информационной системы: управление профилями пациентов, ведение медицинских записей с ICD-10 кодированием, ролевое разграничение доступа и полный audit trail.

Проект намеренно спроектирован как **модульный монолит** - архитектура, которая позволяет начать быстро, сохраняя возможность декомпозиции на микросервисы по мере роста нагрузки или команды. Каждый модуль (`auth`, `patients`, `records`, `audit`) имеет чёткие границы и может быть выделен в отдельный сервис без переработки бизнес-логики.

---

## Архитектурные решения

1. **Почему модульный монолит, а не сразу микросервисы?**  
    - Для MVP с одной командой разработки микросервисы добавляют операционную сложность без реальной выгоды. Текущая структура позволяет применить Strangler Fig Pattern при необходимости выделения сервисов.
2. **Почему async SQLAlchemy + asyncpg?**  
    - Медицинские системы имеют пиковые нагрузки (утренний обход, приёмные часы). Async I/O позволяет обслуживать больше одновременных запросов без увеличения числа воркеров.
3. **Почему Redis для JWT blacklist, а не БД?**  
    - Проверка токена происходит на каждый запрос. TTL-based хранилище в Redis даёт O(1) lookup без нагрузки на PostgreSQL и автоматически очищает истёкшие токены.
4. **Почему soft delete?**  
    - В медицинских системах удаление данных регулируется законодательством (152-ФЗ, приказ МЗ №347н). Физическое удаление недопустимо - данные должны быть доступны для аудита.
5. **Почему UUID вместо serial?**  
    - UUID первичные ключи безопасны при возможной будущей декомпозиции - не будет коллизий между сервисами, и ID не раскрывают информацию о количестве записей.

---

## Стек

|                |                                      |
|----------------|--------------------------------------|
| **Runtime**    | Python 3.12, FastAPI 0.115           |
| **Database**   | PostgreSQL 16, SQLAlchemy 2.0 async  |
| **Cache**      | Redis 7                              |
| **Auth**       | JWT (python-jose), bcrypt (passlib)  |
| **Migrations** | Alembic (autogenerate)               |
| **Deploy**     | Docker, Docker Compose, Nginx        |
| **Tests**      | pytest-asyncio, httpx ASGI transport |

---

## Структура проекта
```text
src/app/
├── core/           # Инфраструктурный слой
│   ├── config.py       # pydantic-settings, все переменные окружения
│   ├── database.py     # async engine, session factory
│   ├── redis.py        # Redis client wrapper
│   ├── security.py     # JWT create/decode, bcrypt
│   ├── exceptions.py   # Иерархия исключений с HTTP статусами
│   └── logging.py      # structlog structured logging
├── models/         # SQLAlchemy ORM (Single Source of Truth для схемы БД)
├── schemas/        # Pydantic v2 DTO (валидация запросов/ответов)
├── modules/        # Бизнес-модули — каждый содержит router/service/repository
│   ├── auth/
│   ├── patients/
│   ├── records/
│   └── audit/
└── utils/          # FHIR helpers, пагинация
```

---

## Доменная модель
```
users ──────────────────────────────────────┐
  id, email, role, is_active                │ doctor_id
  roles: admin|doctor|nurse|receptionist    │
                                            ▼
patients ─────────────────────► medical_records
  id, fhir_id                   id, fhir_resource_id
  blood_type, allergies         record_type, status
  soft_delete                   icd_code, metadata_json
                                lifecycle: draft→final→amended
                                        │
                                        ▼
                                audit_logs
                                action, resource_type
                                ip_address, changes (JSON)
```

---

## RBAC

|                                   | admin | doctor | nurse | receptionist |
|-----------------------------------|----|-----|-----|----|
| Пациенты: создать/читать/обновить | ✅ | ✅ | ✅ | ✅ |
| Пациенты: удалить                 | ✅ | ❌ | ❌ | ❌ |
| Записи: создать                   | ✅ | ✅ | ✅ | ❌ |
| Записи: читать                    | ✅ | Только свои | ✅ | ❌ |
| Записи: удалить                   | ✅ | ❌ | ❌ | ❌ |
| Audit log                         | ✅ | ❌ | ❌ | ❌ |

---

## Жизненный цикл медицинской записи
```
DRAFT ──► FINAL ──► AMENDED
  │                    │
  └────────────────────┴──► CANCELLED
```

Финализированную запись нельзя редактировать напрямую — требуется перевод в `amended`. Это обеспечивает целостность медицинской документации и соответствие требованиям аудита.

---

## Запуск
```bash
git clone https://github.com/kin1x/emr-lite.git
cd emr-lite
cp .env.example .env
make up
make migrate
make seed     # тестовые данные: 4 пользователя, 5 пациентов, 8 записей
```

- API: http://localhost:8000/docs
- pgAdmin: http://localhost:5050

Тестовые credentials после `make seed`:
```
admin:      admin@emr.local    / Admin123!
doctor:     ivanov@emr.local   / Doctor123!
nurse:      nurse@emr.local    / Nurse123!
```

---

## Тесты
```bash
make test-cov
```
```
33 passed, coverage 65%

unit/test_security.py         — JWT tokens, password hashing
integration/test_auth.py      — register, login, logout, RBAC
integration/test_patients.py  — CRUD, soft delete, search, RBAC
integration/test_records.py   — lifecycle, finalize, RBAC isolation
```

Интеграционные тесты используют реальный PostgreSQL (отдельная БД `emr_test`) и MockRedis — тестируется реальное поведение системы, а не моки.

---

## Документация

- [BRD](docs/requirements/BRD.md) — бизнес-требования, stakeholders, MoSCoW приоритизация, acceptance criteria
- [System Design](docs/architecture/system_design.md) — архитектура, ERD, auth flow, FHIR R4 совместимость, roadmap к микросервисам

---

## Roadmap

- [ ] Alembic downgrade + тесты миграций
- [ ] FHIR R4 REST endpoints (`/fhir/r4/Patient`)
- [ ] Модуль расписания (scheduling)
- [ ] WebSocket уведомления
- [ ] Rate limiting (slowapi)
- [ ] CI/CD (GitHub Actions)

## Author 
Boyarshinov Artem