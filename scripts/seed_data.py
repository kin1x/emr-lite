#!/usr/bin/env python3
"""
Скрипт наполнения БД тестовыми данными для разработки.

Создаёт:
- 1 admin пользователя
- 2 doctor пользователей
- 1 nurse пользователя
- 5 пациентов
- 10 медицинских записей

Использование:
    python scripts/seed_data.py
"""
import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import engine, Base, async_session_maker
from app.core.security import hash_password
from app.core.logging import setup_logging, logger
from app.models.user import User, UserRole
from app.models.patient import Patient, Gender, BloodType
from app.models.medical_record import MedicalRecord, RecordType, RecordStatus
import app.models  # noqa: F401
from app.utils.fhir import generate_fhir_id, generate_fhir_resource_id


USERS = [
    {
        "email": "admin@emr.local",
        "password": "Admin123!",
        "first_name": "Администратор",
        "last_name": "Системы",
        "role": UserRole.ADMIN,
    },
    {
        "email": "ivanov@emr.local",
        "password": "Doctor123!",
        "first_name": "Иван",
        "last_name": "Иванов",
        "role": UserRole.DOCTOR,
    },
    {
        "email": "petrova@emr.local",
        "password": "Doctor123!",
        "first_name": "Мария",
        "last_name": "Петрова",
        "role": UserRole.DOCTOR,
    },
    {
        "email": "nurse@emr.local",
        "password": "Nurse123!",
        "first_name": "Елена",
        "last_name": "Сидорова",
        "role": UserRole.NURSE,
    },
]

PATIENTS = [
    {
        "first_name": "Алексей",
        "last_name": "Смирнов",
        "date_of_birth": date(1980, 5, 15),
        "gender": Gender.MALE,
        "blood_type": BloodType.A_POS,
        "phone": "+79001111111",
        "allergies": "Пенициллин",
    },
    {
        "first_name": "Наталья",
        "last_name": "Козлова",
        "date_of_birth": date(1975, 8, 22),
        "gender": Gender.FEMALE,
        "blood_type": BloodType.B_POS,
        "phone": "+79002222222",
        "chronic_conditions": "Гипертония",
    },
    {
        "first_name": "Дмитрий",
        "last_name": "Новиков",
        "date_of_birth": date(1990, 3, 10),
        "gender": Gender.MALE,
        "blood_type": BloodType.O_POS,
        "phone": "+79003333333",
    },
    {
        "first_name": "Ольга",
        "last_name": "Морозова",
        "date_of_birth": date(1965, 11, 30),
        "gender": Gender.FEMALE,
        "blood_type": BloodType.AB_POS,
        "phone": "+79004444444",
        "chronic_conditions": "Сахарный диабет 2 типа",
        "allergies": "Аспирин",
    },
    {
        "first_name": "Сергей",
        "last_name": "Волков",
        "date_of_birth": date(1995, 7, 4),
        "gender": Gender.MALE,
        "blood_type": BloodType.A_NEG,
        "phone": "+79005555555",
    },
]


async def seed():
    setup_logging()
    logger.info("Starting database seed...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as db:
        # Создаём пользователей
        created_users = []
        for user_data in USERS:
            user = User(
                email=user_data["email"],
                hashed_password=hash_password(user_data["password"]),
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                role=user_data["role"],
            )
            db.add(user)
            created_users.append(user)

        await db.flush()
        logger.info(f"Created {len(created_users)} users")

        # Создаём пациентов
        created_patients = []
        for patient_data in PATIENTS:
            patient = Patient(
                **patient_data,
                fhir_id=generate_fhir_id(),
            )
            db.add(patient)
            created_patients.append(patient)

        await db.flush()
        logger.info(f"Created {len(created_patients)} patients")

        # Врачи для записей
        doctors = [u for u in created_users if u.role == UserRole.DOCTOR]

        # Создаём медицинские записи
        records_data = [
            (created_patients[0], doctors[0], RecordType.CONSULTATION, "Первичный осмотр", "Жалобы на головную боль", "R51"),
            (created_patients[0], doctors[0], RecordType.DIAGNOSIS, "Диагноз: Мигрень", "Установлен диагноз мигрень без ауры", "G43.0"),
            (created_patients[1], doctors[0], RecordType.CONSULTATION, "Плановый осмотр", "Контроль АД", "I10"),
            (created_patients[1], doctors[1], RecordType.PRESCRIPTION, "Назначение антигипертензивных", "Лозартан 50мг 1 раз в день", "I10"),
            (created_patients[2], doctors[1], RecordType.CONSULTATION, "Первичный осмотр", "ОРВИ, температура 38.2", "J06.9"),
            (created_patients[3], doctors[0], RecordType.LAB_RESULT, "Анализ крови на сахар", "Глюкоза 8.2 ммоль/л", "E11"),
            (created_patients[3], doctors[1], RecordType.CONSULTATION, "Коррекция терапии", "Корректировка дозы инсулина", "E11"),
            (created_patients[4], doctors[0], RecordType.CONSULTATION, "Спортивная травма", "Растяжение связок голеностопа", "S93.4"),
        ]

        for patient, doctor, rtype, title, desc, icd in records_data:
            record = MedicalRecord(
                patient_id=patient.id,
                doctor_id=doctor.id,
                record_type=rtype,
                status=RecordStatus.FINAL,
                title=title,
                description=desc,
                icd_code=icd,
                fhir_resource_id=generate_fhir_resource_id("rec"),
            )
            db.add(record)

        await db.commit()
        logger.info(f"Created {len(records_data)} medical records")
        logger.info("Seed completed successfully!")
        logger.info("Credentials:")
        for u in USERS:
            logger.info(f"  {u['role'].value}: {u['email']} / {u['password']}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())