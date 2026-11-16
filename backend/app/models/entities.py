import enum
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class RfpStatus(str, enum.Enum):
    DRAFT = "Draft"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class QuestionStatus(str, enum.Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In Progress"
    ANSWERED = "Answered"
    REVIEWED = "Reviewed"


class ResponseStatus(str, enum.Enum):
    DRAFT = "Draft"
    IN_REVIEW = "In Review"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class ApplicationUser(Base):
    __tablename__ = "application_users"

    UserId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    DisplayName = Column(String(100), nullable=False)
    Email = Column(String(255), unique=True, nullable=False, index=True)
    Role = Column(String(50), nullable=False, default="Contributor")

    # Relationships
    rfps_created = relationship("RFP", back_populates="creator", foreign_keys="RFP.CreatedBy")
    responses_updated = relationship("RFPResponse", back_populates="updater", foreign_keys="RFPResponse.UpdatedBy")
    responses_approved = relationship("RFPResponse", back_populates="approver", foreign_keys="RFPResponse.ApprovedBy")


class RFP(Base):
    __tablename__ = "rfps"

    RfpId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Title = Column(String(255), nullable=False, index=True)
    CustomerName = Column(String(255), nullable=False, index=True)
    Description = Column(Text, nullable=True)
    DueDate = Column(DateTime, nullable=True)
    Status = Column(String(50), nullable=False, default=RfpStatus.DRAFT.value)
    CreatedBy = Column(Integer, ForeignKey("application_users.UserId"), nullable=True)
    CreatedDate = Column(DateTime, default=utcnow, nullable=False)
    UpdatedDate = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    # Relationships
    creator = relationship("ApplicationUser", back_populates="rfps_created", foreign_keys=[CreatedBy])
    questions = relationship("RFPQuestion", back_populates="rfp", cascade="all, delete-orphan", order_by="RFPQuestion.Sequence")
    library_entries = relationship("ResponseLibrary", back_populates="source_rfp")

    __table_args__ = (
        Index("ix_rfps_status_duedate", "Status", "DueDate"),
    )


class RFPQuestion(Base):
    __tablename__ = "rfp_questions"

    QuestionId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    RfpId = Column(Integer, ForeignKey("rfps.RfpId", ondelete="CASCADE"), nullable=False, index=True)
    QuestionText = Column(Text, nullable=False)
    Category = Column(String(100), nullable=True, index=True)
    Sequence = Column(Integer, nullable=False, default=1)
    Status = Column(String(50), nullable=False, default=QuestionStatus.PENDING.value)
    AssignedTo = Column(Integer, ForeignKey("application_users.UserId", ondelete="SET NULL"), nullable=True, index=True)
    CreatedDate = Column(DateTime, default=utcnow, nullable=False)

    # Business rule: Every question belongs to exactly one RFP
    rfp = relationship("RFP", back_populates="questions")
    assigned_user = relationship("ApplicationUser", foreign_keys=[AssignedTo])
    responses = relationship("RFPResponse", back_populates="question", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_rfp_questions_rfpid_seq", "RfpId", "Sequence"),
    )


class RFPResponse(Base):
    __tablename__ = "rfp_responses"

    ResponseId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    QuestionId = Column(Integer, ForeignKey("rfp_questions.QuestionId", ondelete="CASCADE"), nullable=False, index=True)
    ResponseText = Column(Text, nullable=False)
    IsAIGenerated = Column(Boolean, nullable=False, default=False)
    Status = Column(String(50), nullable=False, default=ResponseStatus.DRAFT.value)
    UpdatedBy = Column(Integer, ForeignKey("application_users.UserId"), nullable=True)
    UpdatedDate = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    ApprovedBy = Column(Integer, ForeignKey("application_users.UserId"), nullable=True)
    ApprovedDate = Column(DateTime, nullable=True)

    # Business rule: Every response belongs to exactly one question
    question = relationship("RFPQuestion", back_populates="responses")
    updater = relationship("ApplicationUser", back_populates="responses_updated", foreign_keys=[UpdatedBy])
    approver = relationship("ApplicationUser", back_populates="responses_approved", foreign_keys=[ApprovedBy])
    versions = relationship("ResponseVersion", back_populates="response", cascade="all, delete-orphan", order_by="ResponseVersion.VersionNumber.desc()")

    __table_args__ = (
        Index("ix_rfp_responses_question_status", "QuestionId", "Status"),
    )


class ResponseVersion(Base):
    __tablename__ = "response_versions"

    VersionId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ResponseId = Column(Integer, ForeignKey("rfp_responses.ResponseId", ondelete="CASCADE"), nullable=False, index=True)
    ResponseText = Column(Text, nullable=False)
    VersionNumber = Column(Integer, nullable=False, default=1)
    UpdatedBy = Column(Integer, ForeignKey("application_users.UserId"), nullable=True)
    UpdatedDate = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    response = relationship("RFPResponse", back_populates="versions")
    updater = relationship("ApplicationUser", foreign_keys=[UpdatedBy])

    __table_args__ = (
        Index("ix_response_versions_response_version", "ResponseId", "VersionNumber", unique=True),
    )


class ResponseLibrary(Base):
    __tablename__ = "response_library"

    LibraryId = Column(Integer, primary_key=True, index=True, autoincrement=True)
    Question = Column(Text, nullable=False)
    Answer = Column(Text, nullable=False)
    Category = Column(String(100), nullable=True, index=True)
    Technology = Column(String(100), nullable=True, index=True)
    SourceRfpId = Column(Integer, ForeignKey("rfps.RfpId", ondelete="SET NULL"), nullable=True, index=True)
    CreatedDate = Column(DateTime, default=utcnow, nullable=False)

    # Relationships
    source_rfp = relationship("RFP", back_populates="library_entries")

    __table_args__ = (
        Index("ix_response_library_cat_tech", "Category", "Technology"),
    )
