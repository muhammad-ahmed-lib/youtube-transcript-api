from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
    CouldNotRetrieveTranscript,
)
from pydantic import BaseModel
from typing import List
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────

class TranscriptItem(BaseModel):
    start: float
    duration: float
    text: str

class TranscriptResponse(BaseModel):
    videoId: str
    transcript: List[TranscriptItem]

# ── Helpers ───────────────────────────────────────────────────────────────────

_VIDEO_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|embed/|shorts/|/v/)([0-9A-Za-z_-]{11})"
)

def extract_video_id(url_or_id: str) -> str:
    """Return the 11-char video ID from a URL or a bare ID."""
    url_or_id = url_or_id.strip()
    m = _VIDEO_ID_RE.search(url_or_id)
    if m:
        return m.group(1)
    # Already a bare ID?
    if re.fullmatch(r"[0-9A-Za-z_-]{11}", url_or_id):
        return url_or_id
    raise ValueError(f"Cannot extract a video ID from: {url_or_id!r}")

# ── Route ─────────────────────────────────────────────────────────────────────

PREFERRED_LANGS = ["en", "en-US", "en-GB"]

@app.get("/api/transcript/{video_identifier:path}", response_model=TranscriptResponse)
def get_transcript(video_identifier: str):
    # 1. Extract video ID
    try:
        video_id = extract_video_id(video_identifier)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # 2. Fetch transcript using the NEW instance-based API
    ytt = YouTubeTranscriptApi()

    try:
        transcript_list = ytt.list(video_id)

        # Priority: manual EN → auto-generated EN → any available track
        try:
            transcript = transcript_list.find_manually_created_transcript(PREFERRED_LANGS)
        except NoTranscriptFound:
            try:
                transcript = transcript_list.find_generated_transcript(PREFERRED_LANGS)
            except NoTranscriptFound:
                # Fall back to whatever YouTube has first
                transcript = next(iter(transcript_list))

        entries = transcript.fetch()

    except TranscriptsDisabled:
        raise HTTPException(
            status_code=400,
            detail=f"Transcripts are disabled for video '{video_id}'.",
        )
    except VideoUnavailable:
        raise HTTPException(
            status_code=404,
            detail=f"Video '{video_id}' is unavailable or does not exist.",
        )
    except CouldNotRetrieveTranscript as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except StopIteration:
        raise HTTPException(
            status_code=404,
            detail=f"No transcripts found for video '{video_id}'.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error for video '{video_id}': {exc}",
        )

    # 3. Build response — FetchedTranscriptSnippet is a dataclass with .text / .start / .duration
    items = [
        TranscriptItem(
            start=snippet.start,
            duration=snippet.duration,
            text=snippet.text.replace("\n", " "),
        )
        for snippet in entries
    ]

    return TranscriptResponse(videoId=video_id, transcript=items)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)