# Memora — AR-Based Cognitive Assistive Platform

Memora is an AR-based cognitive assistive platform concept designed to support early-stage Alzheimer’s patients. The project explores how augmented reality, facial recognition, age-progression-tolerant identity matching, lifelong learning, and voice-based NLP prompts can help users recognize familiar people and recall important contextual information.

The goal of Memora is to provide gentle, real-time memory assistance in everyday interactions.

---

## 🧠 Problem Statement

Early-stage Alzheimer’s patients may experience difficulty recognizing people, recalling relationships, remembering names, or connecting faces with personal context. These challenges can affect confidence, independence, and social interaction.

Memora aims to assist users by combining computer vision and natural language interaction into an accessible AR-based support system.

---

## 🎯 Objective

The objective of this project is to design a cognitive assistive platform that can:

- Recognize familiar people in real time
- Provide contextual memory cues
- Support voice-based interaction
- Adapt as a person’s appearance changes over time
- Improve assistance through lifelong learning
- Offer a non-intrusive experience through AR-based prompts

---

## 🚀 Key Features

### Face Recognition

Memora is designed to identify known people using facial recognition and retrieve relevant information about them.

Example memory cues:

- Name
- Relationship to the user
- Recent interaction notes
- Important personal context
- Reminders linked to that person

---

### Age-Progression Tolerance

A major challenge in face recognition is that people’s appearances change over time.

Memora considers age-progression-tolerant recognition so that the system can remain useful even when a person looks older, has changed hairstyle, wears glasses, or has other visual differences.

---

### Lifelong Learning

The system is designed to improve continuously as new interactions happen.

Potential lifelong learning behavior:

- Add new faces
- Update existing face profiles
- Improve recognition confidence
- Store new relationship context
- Adapt to changes in appearance

---

### Voice-Based NLP Prompts

Memora uses voice-based prompts to make the system easier for patients to interact with.

Example prompts:

```text id="t8hq0b"
Who is this person?
```

```text id="81pp6r"
How do I know them?
```

```text id="qtayvv"
When did I last meet them?
```

```text id="xcxqhn"
Tell me something important about them.
```

The system can respond with simple, patient-friendly memory cues.

---

### AR-Based Assistance

Instead of requiring users to open a complex app interface, Memora is designed around AR-based contextual assistance.

Possible AR display cues:

* Person’s name
* Relationship label
* Confidence level
* Short memory note
* Voice interaction option

---

## 🏗️ Proposed System Architecture

```text id="zg73at"
Camera / AR Device
        |
        v
Face Detection Module
        |
        v
Face Recognition + Age-Tolerant Matching
        |
        v
Known Person Database
        |
        v
Context Retrieval
        |
        v
NLP Prompt Handler
        |
        v
AR / Voice-Based Memory Cue
```

---

## 🔁 Workflow

```text id="9xde16"
1. User looks at or scans a person through the AR interface.

2. The system detects a face in the camera feed.

3. Facial features are extracted and compared with known profiles.

4. If a match is found, the system retrieves contextual information.

5. The user receives memory cues through AR overlays or voice output.

6. New information can be saved to improve future recognition.
```

---

## 🧩 Core Modules

### 1. Face Detection

Responsible for identifying faces from camera input.

Possible approaches:

* OpenCV-based detection
* MediaPipe face detection
* Deep learning-based face detectors

---

### 2. Face Recognition

Responsible for matching detected faces against known identities.

Possible approaches:

* Face embeddings
* Similarity matching
* Vector-based identity search
* Confidence thresholding

---

### 3. Age-Progression Handling

Responsible for improving recognition despite changes in appearance.

Possible approaches:

* Multiple embeddings per person
* Periodic profile updates
* Time-aware identity matching
* Appearance-change tolerance

---

### 4. Memory Context Store

Stores information linked to known people.

Example data:

```json id="zeyyw6"
{
  "person_id": "001",
  "name": "Ananya",
  "relationship": "Daughter",
  "notes": [
    "Visited last Sunday",
    "Lives in Bengaluru",
    "Usually calls every evening"
  ],
  "last_interaction": "2026-04-20"
}
```

---

### 5. NLP Prompt System

Handles user questions and generates simple responses.

Example:

```text id="20v7bw"
User: Who is this?
System: This is Ananya, your daughter. She visited you last Sunday.
```

---

### 6. AR Output Layer

Displays memory cues in a clear, non-overwhelming format.

Design priorities:

* Minimal text
* High readability
* Calm interface
* Simple voice support
* Low cognitive load

---

## Tech Stack

### AR / Frontend

* Unity with AR Foundation
* Android ARCore
* iOS ARKit
* React Native or Flutter for mobile interface

### Computer Vision

* Python
* OpenCV
* MediaPipe
* face-recognition
* DeepFace
* InsightFace

### Backend

* FastAPI or Flask
* REST APIs
* Authentication
* Profile and memory data management

### Database

* SQLite for prototype
* PostgreSQL or Supabase for production
* Vector database for face embeddings if needed

### AI / NLP

* Gemini, OpenAI, or local NLP models
* Speech-to-text
* Text-to-speech
* Prompt-based memory assistance

---

## 📚 Learning Outcomes

Through this project, the main learning areas include:

* Applying computer vision to assistive technology
* Understanding face recognition systems
* Thinking about age-tolerant identity matching
* Designing for accessibility and cognitive support
* Building ethical AI systems for sensitive use cases
* Combining AR, NLP, and user-centered design

---

## 👨‍💻 Author

Built by [Kasissnu Ssinha](https://github.com/kasissnu)

---

