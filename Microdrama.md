# AI-Powered Microdrama Timestamp Intelligence System
### Architecture Plan — DD Waves

**Version:** 2.0  
**Date:** 2026-05-14  
**Status:** Architecture Design

> **Scope:** This system analyzes long-form video and outputs structured microdrama timestamps with metadata.
> Editing, clipping, and publishing are handled by the existing DD Waves platform.

---

## Table of Contents

1. [What This System Does](#1-what-this-system-does)
2. [System Flow](#2-system-flow)
3. [Layer 1 — Video Ingestion](#3-layer-1--video-ingestion)
4. [Layer 2 — Video Understanding Pipeline](#4-layer-2--video-understanding-pipeline)
5. [Layer 3 — Story Intelligence Engine](#5-layer-3--story-intelligence-engine)
6. [Layer 4 — Drama Score Engine](#6-layer-4--drama-score-engine)
7. [Layer 5 — Episodic Sequencing Engine](#7-layer-5--episodic-sequencing-engine)
8. [Final Output Schema](#8-final-output-schema)
9. [Technology Stack](#9-technology-stack)
10. [Performance Targets](#10-performance-targets)

---

## 1. What This System Does

**Input:** A long-form video (TV episode, movie, web series)

**Output:** A structured JSON file containing:
- Timestamp ranges (`start_time` → `end_time`) for each microdrama
- Drama score and retention prediction per clip
- Emotion tags, characters, hook caption, cliffhanger text
- Serialized episode ordering across clips

**What this system does NOT do:**
- Edit or cut video
- Render captions or effects
- Publish to any platform

All of that stays in your existing platform. This system is purely the **intelligence layer** that tells your platform *where* to cut and *what* each clip means.

---

## 2. System Flow

```
Long-Form Video (MP4 / MKV / MOV / HLS)
        │
        ▼
┌─────────────────────────────┐
│   Layer 1: Video Ingestion  │
│   Normalize, chunk, extract │
│   audio + frames            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────────────────────────┐
│        Layer 2: Video Understanding             │
│                                                 │
│  Scene Detection → ASR → Speaker Diarization   │
│  → Emotion Detection → Audio Analysis → OCR    │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│      Layer 3: Story Intelligence Engine         │
│                                                 │
│  Gemini 2.5 Pro — understands conflict,        │
│  betrayal, suspense, cliffhangers, emotion arc  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│        Layer 4: Drama Score Engine              │
│                                                 │
│  Ranks each candidate by composite drama score  │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│      Layer 5: Episodic Sequencing Engine        │
│                                                 │
│  Orders clips into serialized episode arcs      │
│  with narrative continuity                      │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │   OUTPUT: timestamps.json│
         │   → Sent to DD Waves    │
         │     platform            │
         └─────────────────────────┘
```

---

## 3. Layer 1 — Video Ingestion

### Responsibilities

- Accept video in supported formats
- Extract audio track (for ASR and audio analysis)
- Sample frames (for emotion and OCR)
- Chunk long videos into parallel-processable segments

### Supported Inputs

| Format | Method |
|---|---|
| MP4, MOV, MKV | File upload or S3/GCS URI |
| HLS `.m3u8` | Stream download |

### Preprocessing Steps

1. Transcode to H.264 baseline (FFmpeg) for consistent frame extraction
2. Extract audio → WAV 16kHz mono (for ASR and audio analysis)
3. Sample frames at 1fps → JPEG (for emotion and OCR models)
4. Chunk into 10-minute segments with 30-second overlap for parallel processing

### Output

```json
{
  "job_id": "uuid-v4",
  "source": "s3://bucket/input/episode.mp4",
  "duration_seconds": 2700,
  "chunks": [
    {
      "chunk_id": 0,
      "start": 0,
      "end": 630,
      "audio_path": "s3://bucket/chunks/chunk_0.wav",
      "frames_path": "s3://bucket/chunks/chunk_0_frames/"
    }
  ]
}
```

---

## 4. Layer 2 — Video Understanding Pipeline

Converts raw video into structured data. All components run in parallel per chunk.

---

### 4.1 Scene Detection

Splits the video into semantic scenes at shot boundaries.

**Library:** `PySceneDetect` (content-aware), `OpenCV` (fallback)

**Output:**
```json
{
  "scenes": [
    {
      "scene_id": 12,
      "start_time": "00:12:15",
      "end_time": "00:13:02",
      "duration_seconds": 47
    }
  ]
}
```

---

### 4.2 Speech Recognition (ASR)

Transcribes all dialogue with word-level timestamps.

**Library:** `Whisper Large v3` (primary), `Deepgram Nova-2` (cloud fallback)

**Output:**
```json
{
  "transcript": [
    {
      "start": 742.1,
      "end": 745.8,
      "speaker": "SPEAKER_00",
      "text": "You lied to me for years."
    }
  ]
}
```

---

### 4.3 Speaker Diarization

Identifies and labels individual speakers.

**Library:** `Pyannote Audio 3.1`

**Output:**
```json
{
  "speakers": [
    {
      "speaker_id": "SPEAKER_00",
      "label": "Mother",
      "segments": [
        { "start": 742.1, "end": 745.8 }
      ]
    }
  ]
}
```

---

### 4.4 Emotion Detection

Detects facial and vocal emotion per scene.

**Models:** Vision Transformer (ViT) for face, audio emotion model for voice

**Detected classes:** `anger` · `sadness` · `crying` · `shock` · `happiness` · `fear` · `tension` · `neutral`

**Output:**
```json
{
  "emotions": [
    {
      "timestamp": 742.5,
      "speaker": "SPEAKER_00",
      "face_emotion": "anger",
      "face_confidence": 0.92,
      "voice_emotion": "anger",
      "composite_score": 0.90
    }
  ]
}
```

---

### 4.5 Audio Intensity Analysis

Detects dramatic audio events — screaming, silence, music swells, tension peaks.

**Output:**
```json
{
  "audio_events": [
    {
      "start": 742.0,
      "end": 746.0,
      "type": "dialogue_peak",
      "intensity_db": -12.4,
      "drama_signal": "high"
    },
    {
      "start": 746.0,
      "end": 748.5,
      "type": "silence",
      "drama_signal": "tension"
    }
  ]
}
```

---

### 4.6 OCR Text Analysis

Extracts on-screen text — burned-in subtitles, title cards, phone message screens.

**Library:** `PaddleOCR` (primary), `EasyOCR` (fallback)

**Output:**
```json
{
  "ocr_detections": [
    {
      "timestamp": 743.0,
      "text": "3 years ago...",
      "type": "title_card",
      "confidence": 0.97
    }
  ]
}
```

---

## 5. Layer 3 — Story Intelligence Engine

> **This is the core of the system.** Everything in Layer 2 produces raw signals. This layer produces narrative understanding.

### What It Understands

- Emotional conflict and escalation arcs
- Betrayal and revelation moments
- Romantic tension and chemistry
- Suspense buildup and unresolved endings
- Cliffhanger potential
- Character dynamics and power shifts
- Narrative positioning: setup / confrontation / climax

### Engine

Powered by **Gemini 2.5 Pro** (multimodal). Receives all Layer 2 structured data per scene group and returns ranked microdrama candidates with timestamps.

### System Prompt

```
You are an elite OTT microdrama editor and cinematic storytelling analyst.

Your task is to analyze structured entertainment scene data and identify
the highest-potential segments for short-form vertical microdrama episodes.

You think like:
- A Netflix trailer editor focused on emotional pacing
- A viral short-form strategist who understands platform retention mechanics
- A cinematic storytelling expert who tracks character arcs and tension

Your goal is NOT summarization.
Your goal is to identify 30–90 second narrative windows that:
  - Start with an emotional hook strong enough to stop scrolling in 3 seconds
  - Contain escalating conflict or tension in the middle
  - End with an unresolved cliffhanger — NEVER resolve the scene

For each candidate, return:
1. Exact start_time and end_time (HH:MM:SS format)
2. Emotional hook description
3. Central conflict type
4. Dramatic peak timestamp
5. Cliffhanger ending description
6. Binge-worthy title
7. First-3-second hook caption text
8. Retention score (0–100)
9. Characters present
10. Why this clip performs on short-form platforms

PRIORITIZE scenes with:
- Facial reaction shots (shock, tears, rage)
- Emotionally loaded dialogue
- Dramatic pauses followed by music swells
- Unresolved endings
- Power reversals and betrayal reveals

AVOID scenes with:
- Slow exposition
- Resolved conclusions
- Repetitive low-emotion dialogue

Return structured JSON only. No prose.
```

### User Prompt Template

```
Analyze the following scene data from a long-form video.

Job ID: {job_id}
Source Title: {title}
Language: {language}

SCENE LIST:
{scene_json}

TRANSCRIPT:
{transcript_json}

EMOTION TIMELINE:
{emotion_json}

AUDIO EVENTS:
{audio_events_json}

Generate microdrama candidates between 30–90 seconds each.
Return JSON matching the MicrodramaCandidate schema.
```

---

## 6. Layer 4 — Drama Score Engine

Assigns a composite score to every candidate scene to rank and filter output.

### Formula

```
drama_score = (
    emotion_intensity    × 0.35  +
    face_reaction_peak   × 0.20  +
    dialogue_aggression  × 0.20  +
    silence_tension      × 0.15  +
    audio_peak           × 0.10
)
```

All inputs normalized to [0.0, 1.0]. Final score: **0–100**.

### Score Tiers

| Score | Tier | Action |
|---|---|---|
| 85–100 | Tier 1 — Premium Drama | Always include |
| 65–84 | Tier 2 — High Drama | Include |
| 45–64 | Tier 3 — Moderate | Include if episode count target not met |
| < 45 | Low Drama | Exclude |

### Bonus Signals

| Signal | Adjustment |
|---|---|
| Unresolved narrative ending | +10 pts cliffhanger bonus |
| Character recurrence across scenes | ×1.1 multiplier |
| Music bed type = tension / sting | +5 pts |

---

## 7. Layer 5 — Episodic Sequencing Engine

Orders selected clips into a coherent serialized series rather than a random list.

### Character Relationship Graph

Built from transcript and story intelligence output. Used to group clips by character arc.

```json
{
  "characters": [
    { "id": "char_01", "name": "Mother", "role": "protagonist" },
    { "id": "char_02", "name": "Son", "role": "antagonist" }
  ],
  "relationships": [
    {
      "from": "char_01",
      "to": "char_02",
      "type": "parent_child",
      "arc": "betrayal_discovery",
      "tension": "high"
    }
  ]
}
```

### Sequencing Algorithm

```
1. Cluster candidates by shared character arc and conflict type
2. Score narrative dependency (does clip B reference clip A's context?)
3. Order: setup → escalation → confrontation → peak → unresolved
4. Assign episode numbers with consistent series title
5. Link cliffhangers across episodes (episode N ends → episode N+1 begins)
```

---

## 8. Final Output Schema

This is the only output your platform needs to consume. Everything else (editing, clipping, captions, publishing) is handled by your existing systems.

### Top-Level Job Result

```json
{
  "job_id": "uuid-v4",
  "source_title": "Annamalai - Episode 42",
  "language": "te",
  "duration_seconds": 2700,
  "total_scenes_analyzed": 187,
  "microdramas_generated": 38,
  "series": [
    {
      "series_id": "series_001",
      "series_title": "The Betrayal — Mother & Son Arc",
      "total_episodes": 8,
      "episodes": [ ... ]
    }
  ],
  "created_at": "2026-05-14T09:00:00Z"
}
```

### Per-Episode Timestamp Record

```json
{
  "episode_number": 2,
  "series_id": "series_001",
  "clip_id": "md_001",

  "title": "She Finally Exposed Him",
  "start_time": "00:12:15",
  "end_time": "00:13:02",
  "duration_seconds": 47,

  "hook_caption": "Nobody expected her to reveal this...",
  "hook_timestamp": "00:12:15",
  "dramatic_peak_time": "00:12:48",
  "cliffhanger": "But then the father walked in...",

  "drama_score": 91.4,
  "retention_score": 94,
  "viral_potential": "high",

  "emotion_types": ["betrayal", "anger", "shock"],
  "characters": [
    { "name": "Mother", "role": "protagonist" },
    { "name": "Son", "role": "antagonist" }
  ],
  "conflict_type": "betrayal_reveal",
  "narrative_arc_position": "confrontation",

  "viral_reason": "Strong emotional conflict with unresolved ending. High-reaction shot at 00:12:48."
}
```

---

## 9. Technology Stack

| Layer | Tool | Purpose |
|---|---|---|
| Story Intelligence | Gemini 2.5 Pro | Narrative understanding, timestamp selection |
| ASR | Whisper Large v3 | Dialogue transcription |
| ASR fallback | Deepgram Nova-2 | Speed-optimized cloud transcription |
| Speaker ID | Pyannote Audio 3.1 | Speaker diarization |
| Emotion | ViT-based face model | Facial emotion per timestamp |
| Scene Detection | PySceneDetect | Shot boundary detection |
| OCR | PaddleOCR | On-screen text extraction |
| Audio Analysis | Librosa / custom | RMS, silence, peak event detection |
| API | FastAPI | Job submission and result retrieval |
| Queue | Celery + Redis | Async parallel processing |
| Storage | AWS S3 / GCS | Intermediate data and output JSON |
| Database | PostgreSQL | Job state and metadata |

---

## 10. Performance Targets

| Metric | Target |
|---|---|
| Processing time (45-min episode) | < 45 minutes |
| Drama score agreement with human editor | ≥ 85% overlap |
| Cliffhanger detection recall | ≥ 90% |
| False positive rate (low-drama clips scoring high) | < 10% |
| Output format: valid parseable JSON | 100% |

---

*DD Waves — AI-Powered Microdrama Timestamp Intelligence System*  
*Version 2.0 | 2026-05-14*
