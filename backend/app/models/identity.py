from datetime import date, time

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin, UserRole, gen_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    patient: Mapped["Patient"] = relationship(back_populates="user", uselist=False)
    doctor: Mapped["Doctor"] = relationship(back_populates="user", uselist=False)


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    contact_information: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="patient")


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    qualification: Mapped[str | None] = mapped_column(String(255), nullable=True)
    experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    slot_duration: Mapped[int] = mapped_column(Integer, default=30, nullable=False)  # minutes
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship(back_populates="doctor")
    working_hours: Mapped[list["DoctorWorkingHours"]] = relationship(back_populates="doctor")
    leaves: Mapped[list["DoctorLeave"]] = relationship(back_populates="doctor")


class DoctorWorkingHours(Base):
    __tablename__ = "doctor_working_hours"
    __table_args__ = (UniqueConstraint("doctor_id", "day_of_week", name="uq_doctor_day"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True, nullable=False)
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Monday .. 6=Sunday
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    doctor: Mapped["Doctor"] = relationship(back_populates="working_hours")


class DoctorLeave(Base, TimestampMixin):
    __tablename__ = "doctor_leaves"
    __table_args__ = (UniqueConstraint("doctor_id", "leave_date", name="uq_doctor_leave_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    doctor_id: Mapped[str] = mapped_column(String(36), ForeignKey("doctors.id"), index=True, nullable=False)
    leave_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    doctor: Mapped["Doctor"] = relationship(back_populates="leaves")
