# main/services/llm_answers_schemas.py

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class IsResumeSchema(BaseModel):
    is_resume: Literal[
        "0",
        "1"
    ] = Field(
        description="is this mail a cv: 0-it is not cv, 1-yes, it is cv"
    )


class CandidateInfoFromResume(BaseModel):
    full_name: str = Field(
        description="Full name of the candidate extracted from the resume."
    )

    programming_languages: str = Field(
        description="List of programming languages known by the candidate. "
                    "Format: one language per line. "
                    "Example: 'Python\nJavaScript\nC++'"
    )

    work_experience: str = Field(
        description="Work history including company name and duration. "
                    "Format: 'Company Name Duration' per line. "
                    "Example: 'ElevenLabs 1.5 years\nMbank 2 years'"
    )

    technologies: str = Field(
        description="Technological stack, frameworks, and libraries. "
                    "Format: one technology per line. "
                    "Example: 'Django\nFastAPI\nPostgreSQL'"
    )

    education: str = Field(
        description="Educational background (university, degree, courses). "
                    "Format: each institution/degree on a new line."
    )

    soft_skills: str = Field(
        description="Assessment of soft skills based on the cover letter and resume tone. "
                    "List key soft skills or the evaluation summary, separated by newlines."
    )

    spoken_languages: str = Field(
        description="Spoken languages and proficiency levels. "
                    "Format: 'Language Level' per line. "
                    "Example: 'English B2\nRussian Native'"
    )

    email: Optional[str] = Field(
        description="Contact email address of the candidate. If not found, return null or empty string.",
        default=None
    )

    phone: Optional[str] = Field(
        description="Contact phone number of the candidate. If not found, return null or empty string.",
        default=None
    )

    telegram: Optional[str] = Field(
        description="Telegram username or profile link. If not found, return null or empty string.",
        default=None
    )


class IsRelevantCandidate(BaseModel):
    is_relevant: Literal["0", "1"] = Field(
        description=(
            "Compare the candidate's skills and experience with the position requirements. "
            "Return '1' if there is a strong match, '0' if the candidate is unqualified or irrelevant."
        )
    )