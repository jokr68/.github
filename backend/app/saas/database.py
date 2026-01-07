"""
Database Models: 8 جداول متكاملة باستخدام SQLAlchemy

هذا الملف يعرّف نماذج قاعدة البيانات الأساسية للتطبيق باستخدام
SQLAlchemy ORM. يشتمل على ثمانية جداول تمثل الكيانات الرئيسية
للمنصة مثل المستخدمين، الاشتراكات، المحادثات، الرسائل، سجلات
الاستخدام، الشخصيات، تفضيلات الشخصيات، والملفات المرفوعة.

تم تصميم الحقول بعناية لدعم متطلبات نظام "أثير" مع الأخذ بعين
الاعتبار توسيع الخدمات لاحقًا، بما في ذلك SaaS ووكيل ذكي.
"""

from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    Float,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.dialects import postgresql
import uuid
from datetime import datetime

from app.core.config import settings


Base = declarative_base()


class GUID(TypeDecorator):
    """UUID portable بين SQLite/PostgreSQL."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return str(value)
        return str(uuid.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        try:
            return uuid.UUID(str(value))
        except Exception:
            return value


class User(Base):
    """جدول المستخدمين"""

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)
    plan_tier = Column(String(50), default="free", nullable=False, index=True)
    stripe_customer_id = Column(
        String(255), unique=True, nullable=True, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # العلاقات
    subscriptions = relationship("Subscription", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    usage_logs = relationship("UsageLog", back_populates="user")
    personas = relationship("Persona", back_populates="user")
    files = relationship("FileUpload", back_populates="user")


class Subscription(Base):
    """جدول الاشتراكات (SaaS)"""

    __tablename__ = "subscriptions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=True, index=True)
    stripe_subscription_id = Column(
        String(255), unique=True, nullable=False, index=True
    )
    stripe_customer_id = Column(String(255), nullable=False, index=True)
    price_id = Column(String(255), nullable=True)
    tier = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # active, canceled, past_due
    current_period_end = Column(DateTime, nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    cancel_at = Column(DateTime, nullable=True)
    canceled_at = Column(DateTime, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    last_invoice_id = Column(String(255), nullable=True)
    last_payment_status = Column(String(50), nullable=True)
    last_payment_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # العلاقات
    user = relationship("User", back_populates="subscriptions")


class Conversation(Base):
    """جدول المحادثات"""

    __tablename__ = "conversations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    status = Column(String(50), default="active", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # العلاقات
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")


class Message(Base):
    """جدول الرسائل داخل المحادثات"""

    __tablename__ = "messages"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(GUID(), ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # العلاقات
    conversation = relationship("Conversation", back_populates="messages")


class UsageLog(Base):
    """سجلات الاستخدام للأدوات والتكاليف"""

    __tablename__ = "usage_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    cost = Column(Float, nullable=False)
    execution_time_ms = Column(Integer, nullable=True)
    extra = Column(JSON, nullable=True)  # يمكن تخزين بيانات إضافية عن التنفيذ
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="usage_logs")


class Persona(Base):
    """جدول الشخصيات المخصصة للمستخدمين"""

    __tablename__ = "personas"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # العلاقات
    user = relationship("User", back_populates="personas")
    preferences = relationship(
        "PersonaPreference", back_populates="persona", cascade="all, delete-orphan"
    )


class PersonaPreference(Base):
    """تفضيلات الشخصية المرتبطة بشخصية معينة"""

    __tablename__ = "persona_preferences"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    persona_id = Column(GUID(), ForeignKey("personas.id"), nullable=False, index=True)
    key = Column(String(100), nullable=False, index=True)
    value = Column(JSON, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    persona = relationship("Persona", back_populates="preferences")


class FileUpload(Base):
    """ملفات مرفوعة من قبل المستخدمين"""

    __tablename__ = "file_uploads"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    path = Column(String(500), nullable=False)
    size = Column(Integer, nullable=True)
    mime_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="files")


class ConversationSummary(Base):
    """طبقة ملخصات المحادثة (Layer 4 في الذاكرة).

    تُخزن ملخصات قصيرة قابلة للاسترجاع بسرعة، وتُستخدم لتقليل حجم السياق
    وإعطاء الوكيل صورة عامة عن سياق الحوار.
    """

    __tablename__ = "conversation_summaries"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(GUID(), ForeignKey("conversations.id"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    tokens_estimate = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_conversation_summaries_conv_created", "conversation_id", "created_at"),
    )


# إعداد المحرك وصانع الجلسات (يُقرأ من الإعدادات)
DATABASE_URL = settings.DATABASE_URL


def _sqlite_connect_args(url: str):
    if url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=_sqlite_connect_args(DATABASE_URL),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """إنشاء كافة الجداول في قاعدة البيانات"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency لـFastAPI: يوفّر Session ويغلقه بعد الانتهاء."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()