# Consult Suggestions + Consultation/Chat Screen Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the AI chatbot's high/medium risk detection into a patient-facing suggestion (instead of a silent auto-escalation), and split the doctor-only `ConsultationChatScreen` into a `ConsultationScreen` (ticket info/actions) and `ConsultationThreadScreen` (message thread) so patients can reach their own consultations too.

**Architecture:** Backend keeps auto-escalation only for `severity_level == "critical"` (hard safety triggers: suicide/self-harm, chest pain, unconscious, overdose, stroke — explicitly out of scope for this change). For `high`/`medium`, `/chat/` now returns a `consultation_suggestion` object instead of creating a ticket. The Flutter chat screen renders that as an inline card under the latest bot bubble; accepting it calls the existing `POST /consultations/manual` endpoint and opens the newly split `ConsultationScreen`. Separately, `consultation_chat_screen.dart` is split into `ConsultationScreen` (details/actions) and `ConsultationThreadScreen` (messaging), wired into both the doctor navigation flow and the new suggestion-acceptance flow.

**Tech Stack:** FastAPI + SQLAlchemy + pytest (backend), Flutter + Riverpod + flutter_test (frontend).

## Global Constraints

- Critical/hard-safety auto-escalation (self-harm phrases, acute phrases, and the `critical` `RISK_KEYWORDS` list in `backend/app/services/escalation.py`) must NOT change behavior — it keeps auto-creating a ticket immediately, exactly as today.
- Only `evaluate_chat_risk` / the `/chat/` route change. `evaluate_stats_risk` (used by `backend/app/routes/diet.py` and `backend/app/routes/health.py` for wearable/diet-entry based escalation) is out of scope — this task is specifically about chatbot conversation risk.
- `consultation_suggestion` is ephemeral: it is returned only on the immediate `/chat/` response, never persisted on `ChatMessage`, and never appears in `/chat/history`.
- The new patient-facing chat thread screen must be named `ConsultationThreadScreen`, not `ChatScreen` — `ChatScreen` already exists for the AI assistant (`health_app/lib/screens/chat/chat_screen.dart`) and reusing the name would collide.
- No new backend endpoints — reuse `POST /consultations/manual` (already patient-callable) for suggestion acceptance.

---

### Task 1: Backend — suggestion instead of auto-escalation for high/medium chat risk

**Files:**
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/routes/chat.py:94-129`
- Test: `backend/tests/test_chat_escalation.py` (new)

**Interfaces:**
- Consumes: `evaluate_chat_risk(db, user, message) -> dict` with keys `should_escalate: bool`, `severity_score: int`, `severity_level: str` (`"critical"|"high"|"medium"|"low"`), `category_name: str`, `reason: str` (unchanged, from `app/services/escalation.py`). `create_consultation_ticket(db, *, user, trigger_source, trigger_reason, severity_score, category_name) -> ConsultationTicket` (unchanged).
- Produces: `ChatResponse` now has an additional optional field `consultation_suggestion: ConsultationSuggestion | None`, where `ConsultationSuggestion` has `category_name: str`, `severity_level: str`, `reason: str`. Later tasks (Task 2) consume this exact JSON shape (`category_name`, `severity_level`, `reason`) from the HTTP response body key `consultation_suggestion`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_chat_escalation.py`:

```python
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models.diet import DietRecord
from app.models.sleep import SleepRecord
from app.models.user import User


def _signup_and_login(client, email: str, password: str):
    client.post(
        "/users/signup",
        json={"name": "Chat Risk User", "email": email, "password": password},
    )
    login = client.post(
        "/users/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return login.json()["access_token"]


def _grant_consent(client, token: str):
    consent = client.post(
        "/privacy/consent",
        json={"consent_given": True, "consent_version": "v1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert consent.status_code == 200


def test_critical_message_still_auto_escalates(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I have severe chest pain right now"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is True
    assert body["consultation_ticket_id"] is not None
    assert body["consultation_suggestion"] is None

    my_consultations = client.get(
        "/consultations/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert my_consultations.status_code == 200
    assert len(my_consultations.json()) == 1


def test_high_severity_message_suggests_instead_of_escalating(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I think I'm having a panic attack"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["consultation_ticket_id"] is None
    assert body["consultation_suggestion"] is not None
    assert body["consultation_suggestion"]["severity_level"] == "high"

    my_consultations = client.get(
        "/consultations/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert my_consultations.json() == []


def test_medium_severity_message_suggests_instead_of_escalating(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    response = client.post(
        "/chat/",
        json={"message": "I've been struggling with anxiety this week."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["consultation_ticket_id"] is None
    assert body["consultation_suggestion"] is not None
    assert body["consultation_suggestion"]["severity_level"] == "medium"

    my_consultations = client.get(
        "/consultations/my",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert my_consultations.json() == []


def test_low_severity_message_has_no_suggestion(client, random_email):
    token = _signup_and_login(client, random_email, "StrongPass1!")
    _grant_consent(client, token)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == random_email).first()
        now = datetime.utcnow()
        db.add(
            SleepRecord(
                user_id=user.id,
                sleep_start=now - timedelta(hours=7),
                sleep_end=now,
                quality="good",
            )
        )
        db.add(
            DietRecord(
                user_id=user.id,
                meal_type="dinner",
                food="rice and vegetables",
                calories=2000,
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/chat/",
        json={"message": "I went for a walk today and feel fine"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["escalated"] is False
    assert body["consultation_ticket_id"] is None
    assert body["consultation_suggestion"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_chat_escalation.py -v`
Expected: FAIL — `test_high_severity_message_suggests_instead_of_escalating` and `test_medium_severity_message_suggests_instead_of_escalating` fail because today's code auto-creates a ticket for `high` severity too (`should_escalate = severity in {"high", "critical"}`), so `consultation_ticket_id` is not `None` and `my_consultations` is not empty. `test_critical_message_still_auto_escalates` fails on `body["consultation_suggestion"] is None` (KeyError/None mismatch — field doesn't exist yet). `test_low_severity_message_has_no_suggestion` fails the same way (missing field).

- [ ] **Step 3: Add `consultation_suggestion` to the response schema**

In `backend/app/schemas/chat.py`, replace the full file contents with:

```python
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class ConsultationSuggestion(BaseModel):
    category_name: str
    severity_level: str
    reason: str


class ChatResponse(BaseModel):
    response: str
    escalated: bool = False
    consultation_ticket_id: int | None = None
    consultation_status: str | None = None
    doctor_id: int | None = None
    consultation_suggestion: ConsultationSuggestion | None = None
```

- [ ] **Step 4: Change the route to only auto-escalate on `critical`, and suggest on `high`/`medium`**

In `backend/app/routes/chat.py`, change the import on line 6 from:

```python
from app.schemas.chat import ChatRequest, ChatResponse
```

to:

```python
from app.schemas.chat import ChatRequest, ChatResponse, ConsultationSuggestion
```

Then replace lines 94-129 (from `risk = evaluate_chat_risk(...)` through the closing `return ChatResponse(response=reply)`) with:

```python
        risk = evaluate_chat_risk(db, user, request.message)

        if risk["severity_level"] == "critical":
            ticket = create_consultation_ticket(
                db,
                user=user,
                trigger_source="chat",
                trigger_reason=risk["reason"],
                severity_score=risk["severity_score"],
                category_name=risk["category_name"],
            )
            write_audit_log(
                db,
                actor_user_id=user.id,
                actor_role=user.role,
                event_type="chat_escalated",
                target_type="consultation_ticket",
                target_id=str(ticket.id),
                severity=ticket.severity_level,
                metadata={
                    "severity_score": risk["severity_score"],
                    "category_name": risk["category_name"],
                },
            )
            return ChatResponse(
                response=(
                    f"{reply}\n\n"
                    "I detected signs that may need professional attention. "
                    f"A consultation ticket #{ticket.id} has been opened."
                ),
                escalated=True,
                consultation_ticket_id=ticket.id,
                consultation_status=ticket.status,
                doctor_id=ticket.doctor_id,
            )

        if risk["severity_level"] in {"high", "medium"}:
            return ChatResponse(
                response=reply,
                consultation_suggestion=ConsultationSuggestion(
                    category_name=risk["category_name"],
                    severity_level=risk["severity_level"],
                    reason=risk["reason"],
                ),
            )

        return ChatResponse(response=reply)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_chat_escalation.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Run the full backend test suite to check for regressions**

Run: `cd backend && python -m pytest -v`
Expected: All tests pass, including `tests/test_health_endpoints.py::test_chat_with_token` (a plain `"hello"` message from a fresh user lands in `medium` severity due to the existing zero-tracked-data floor in `evaluate_chat_risk`; it already didn't auto-escalate before this change, since `medium` was never in the old `{"high", "critical"}` set, so this test's `assert "response" in response.json()` still holds — it just now also carries a `consultation_suggestion`, which the test doesn't check).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/routes/chat.py backend/tests/test_chat_escalation.py
git commit -m "feat: suggest a consult instead of auto-escalating on high/medium chat risk"
```

---

### Task 2: Frontend — parse `consultation_suggestion` into the chat message model

**Files:**
- Modify: `health_app/lib/models/models.dart:73-115` (the `ChatMessage` class)
- Modify: `health_app/lib/services/api_client.dart:173-201` (`sendMessage`)
- Test: `health_app/test/chat_message_model_test.dart` (new)

**Interfaces:**
- Consumes: backend JSON field `consultation_suggestion: {category_name, severity_level, reason} | null` (Task 1).
- Produces: `ChatMessage.consultationSuggestion: ConsultationSuggestion?`, and a new `ConsultationSuggestion` class with fields `categoryName: String`, `severityLevel: String`, `reason: String` — consumed by Task 4's suggestion card.

- [ ] **Step 1: Write the failing test**

Create `health_app/test/chat_message_model_test.dart`:

```dart
import 'package:flutter_test/flutter_test.dart';
import 'package:health_app/models/models.dart';

void main() {
  group('ChatMessage.fromJson consultation_suggestion', () {
    test('parses a present consultation_suggestion', () {
      final message = ChatMessage.fromJson({
        'id': 1,
        'user_id': '1',
        'message': 'hi',
        'response': 'hello',
        'escalated': false,
        'consultation_suggestion': {
          'category_name': 'Mental Health',
          'severity_level': 'medium',
          'reason': 'Risk detected from chatbot conversation and recent health context.',
        },
        'timestamp': '2026-07-20T00:00:00.000Z',
      });

      expect(message.consultationSuggestion, isNotNull);
      expect(message.consultationSuggestion!.categoryName, 'Mental Health');
      expect(message.consultationSuggestion!.severityLevel, 'medium');
      expect(
        message.consultationSuggestion!.reason,
        'Risk detected from chatbot conversation and recent health context.',
      );
    });

    test('leaves consultation_suggestion null when absent', () {
      final message = ChatMessage.fromJson({
        'id': 1,
        'user_id': '1',
        'message': 'hi',
        'response': 'hello',
        'escalated': false,
        'timestamp': '2026-07-20T00:00:00.000Z',
      });

      expect(message.consultationSuggestion, isNull);
    });
  });
}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd health_app && flutter test test/chat_message_model_test.dart`
Expected: FAIL — compile error, `consultationSuggestion` getter isn't defined on `ChatMessage`.

- [ ] **Step 3: Add the `ConsultationSuggestion` class and wire it into `ChatMessage`**

In `health_app/lib/models/models.dart`, replace the `ChatMessage` class (lines 73-115, from `class ChatMessage {` through its closing `}`) with:

```dart
class ChatMessage {
  final String id;
  final String userId;
  final String message;
  final String response;
  final String? sentiment;
  final List<String>? suggestedActions;
  final bool escalated;
  final String? consultationTicketId;
  final String? consultationStatus;
  final String? doctorId;
  final ConsultationSuggestion? consultationSuggestion;
  final DateTime timestamp;

  ChatMessage({
    required this.id,
    required this.userId,
    required this.message,
    required this.response,
    this.sentiment,
    this.suggestedActions,
    this.escalated = false,
    this.consultationTicketId,
    this.consultationStatus,
    this.doctorId,
    this.consultationSuggestion,
    required this.timestamp,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: (json['id'] ?? '').toString(),
      userId: (json['user_id'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      response: (json['response'] ?? '').toString(),
      sentiment: json['sentiment'],
      suggestedActions: List<String>.from(json['suggested_actions'] ?? []),
      escalated: json['escalated'] == true,
      consultationTicketId: json['consultation_ticket_id']?.toString(),
      consultationStatus: json['consultation_status']?.toString(),
      doctorId: json['doctor_id']?.toString(),
      consultationSuggestion: json['consultation_suggestion'] != null
          ? ConsultationSuggestion.fromJson(json['consultation_suggestion'] as Map<String, dynamic>)
          : null,
      timestamp: DateTime.parse((json['timestamp'] ?? json['recorded_at'] ?? DateTime.now().toIso8601String()).toString()),
    );
  }
}

class ConsultationSuggestion {
  final String categoryName;
  final String severityLevel;
  final String reason;

  ConsultationSuggestion({
    required this.categoryName,
    required this.severityLevel,
    required this.reason,
  });

  factory ConsultationSuggestion.fromJson(Map<String, dynamic> json) {
    return ConsultationSuggestion(
      categoryName: (json['category_name'] ?? '').toString(),
      severityLevel: (json['severity_level'] ?? '').toString(),
      reason: (json['reason'] ?? '').toString(),
    );
  }
}
```

- [ ] **Step 4: Pass the field through in `ApiClient.sendMessage`**

In `health_app/lib/services/api_client.dart`, in `sendMessage` (around lines 183-195), change:

```dart
      return ChatMessage.fromJson({
        'id': DateTime.now().millisecondsSinceEpoch,
        'user_id': '',
        'message': message,
        'response': data['response'] ?? '',
        'escalated': data['escalated'] ?? false,
        'consultation_ticket_id': data['consultation_ticket_id'],
        'consultation_status': data['consultation_status'],
        'doctor_id': data['doctor_id'],
        'timestamp': DateTime.now().toIso8601String(),
      });
```

to:

```dart
      return ChatMessage.fromJson({
        'id': DateTime.now().millisecondsSinceEpoch,
        'user_id': '',
        'message': message,
        'response': data['response'] ?? '',
        'escalated': data['escalated'] ?? false,
        'consultation_ticket_id': data['consultation_ticket_id'],
        'consultation_status': data['consultation_status'],
        'doctor_id': data['doctor_id'],
        'consultation_suggestion': data['consultation_suggestion'],
        'timestamp': DateTime.now().toIso8601String(),
      });
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd health_app && flutter test test/chat_message_model_test.dart`
Expected: PASS (2 passed)

- [ ] **Step 6: Run the full frontend test suite to check for regressions**

Run: `cd health_app && flutter test`
Expected: All tests pass, including the existing `test/widget_test.dart`.

- [ ] **Step 7: Commit**

```bash
git add health_app/lib/models/models.dart health_app/lib/services/api_client.dart health_app/test/chat_message_model_test.dart
git commit -m "feat: parse consultation_suggestion from chat responses"
```

---

### Task 3: Frontend — split `ConsultationChatScreen` into `ConsultationScreen` + `ConsultationThreadScreen`

This is a structural refactor of existing, already-working behavior (accept/close/rate, message thread, websocket handling) — no new logic is introduced, so there is no failing-test step. There is no existing automated widget-test coverage for this screen to preserve (confirmed: only `test/widget_test.dart` exists in the project, covering the app entry screen, not consultations). Verification is `flutter analyze` (must be clean) plus the manual doctor-flow walkthrough in Step 5.

**Files:**
- Create: `health_app/lib/screens/consultation/consultation_screen.dart`
- Create: `health_app/lib/screens/consultation/consultation_thread_screen.dart`
- Modify: `health_app/lib/screens/doctor/doctor_navigation_screen.dart:9,35,44`
- Delete: `health_app/lib/screens/consultation/consultation_chat_screen.dart`

**Interfaces:**
- Consumes: `ConsultationTicket` (`health_app/lib/models/models.dart`), `ApiClient.acceptConsultation/closeConsultation/rateDoctor/getConsultationMessages/consultationChannel` (`health_app/lib/services/api_client.dart`), `myConsultationsProvider`/`consultationQueueProvider`/`authProvider` (`health_app/lib/providers/app_providers.dart`), `StatusPill`/`StatusPillTone` (`health_app/lib/widgets/status_pill.dart`), `LoadingState`/`ErrorState`/`EmptyState` (`health_app/lib/widgets/common_widgets.dart`).
- Produces: `ConsultationScreen({required ConsultationTicket ticket})` — pushed from doctor navigation and from Task 4's suggestion-acceptance flow. `ConsultationThreadScreen({required ConsultationTicket ticket})` — pushed only from `ConsultationScreen`'s "Open Chat" action.

- [ ] **Step 1: Create `consultation_screen.dart`**

Create `health_app/lib/screens/consultation/consultation_screen.dart`:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../models/models.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/status_pill.dart';
import 'consultation_thread_screen.dart';

class ConsultationScreen extends ConsumerStatefulWidget {
  const ConsultationScreen({
    super.key,
    required this.ticket,
  });

  final ConsultationTicket ticket;

  @override
  ConsumerState<ConsultationScreen> createState() => _ConsultationScreenState();
}

class _ConsultationScreenState extends ConsumerState<ConsultationScreen> {
  final TextEditingController _reviewController = TextEditingController();

  bool _joining = false;
  bool _closing = false;
  bool _rating = false;
  int _ratingValue = 5;
  late ConsultationTicket _ticket;

  @override
  void initState() {
    super.initState();
    _ticket = widget.ticket;
  }

  @override
  void dispose() {
    _reviewController.dispose();
    super.dispose();
  }

  Future<void> _acceptConsultation() async {
    setState(() {
      _joining = true;
    });
    try {
      final accepted = await ApiClient.acceptConsultation(_ticket.id);
      if (!mounted) return;
      setState(() {
        _ticket = accepted;
      });
      ref.invalidate(myConsultationsProvider);
      ref.invalidate(consultationQueueProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not accept consultation: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _joining = false;
        });
      }
    }
  }

  Future<void> _closeConsultation() async {
    setState(() {
      _closing = true;
    });
    try {
      final closed = await ApiClient.closeConsultation(_ticket.id);
      if (!mounted) return;
      setState(() {
        _ticket = closed;
      });
      ref.invalidate(myConsultationsProvider);
      ref.invalidate(consultationQueueProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not close consultation: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _closing = false;
        });
      }
    }
  }

  Future<void> _rateDoctor() async {
    setState(() {
      _rating = true;
    });
    try {
      await ApiClient.rateDoctor(
        _ticket.id,
        rating: _ratingValue,
        review: _reviewController.text.trim().isEmpty ? null : _reviewController.text.trim(),
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Thanks for your feedback.')),
      );
      ref.invalidate(myConsultationsProvider);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not submit rating: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _rating = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final currentUser = authState.user;
    final isDoctor = currentUser?.role == 'doctor';
    final canAccept = isDoctor && _ticket.status == 'pending';
    final canClose = _ticket.status != 'closed' && (isDoctor || _ticket.status == 'in_progress' || _ticket.status == 'accepted');

    return Scaffold(
      appBar: AppBar(
        title: Text('Consultation #${_ticket.id}'),
        actions: [
          if (canAccept)
            TextButton(
              onPressed: _joining ? null : _acceptConsultation,
              child: _joining
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Accept'),
            ),
          if (canClose)
            TextButton(
              onPressed: _closing ? null : _closeConsultation,
              child: _closing
                  ? const SizedBox(
                      height: 16,
                      width: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Close'),
            ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: _ticket.severityLevel == 'critical'
                  ? AppColors.error.withValues(alpha: 0.08)
                  : Theme.of(context).colorScheme.primary.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.grey200),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _ticket.triggerReason,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 6),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    StatusPill(label: _ticket.severityLevel.toUpperCase(), tone: _severityTone(_ticket.severityLevel)),
                    StatusPill(label: _ticket.status.toUpperCase(), tone: StatusPillTone.info),
                    StatusPill(label: _ticket.triggerSource.toUpperCase(), tone: StatusPillTone.neutral),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: ListTile(
              leading: const Icon(Icons.chat_bubble_outline),
              title: const Text('Open Chat'),
              subtitle: const Text('View and send messages for this consultation'),
              trailing: const Icon(Icons.chevron_right),
              onTap: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ConsultationThreadScreen(ticket: _ticket),
                  ),
                );
              },
            ),
          ),
          if (_ticket.status == 'closed' && !isDoctor) ...[
            const SizedBox(height: 16),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.grey200),
                borderRadius: BorderRadius.circular(12),
                color: AppColors.surface,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Rate this doctor', style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Row(
                    children: List.generate(5, (index) {
                      final star = index + 1;
                      return IconButton(
                        icon: Icon(
                          star <= _ratingValue ? Icons.star : Icons.star_border,
                          color: Colors.amber,
                        ),
                        onPressed: () => setState(() => _ratingValue = star),
                      );
                    }),
                  ),
                  TextField(
                    controller: _reviewController,
                    decoration: const InputDecoration(
                      hintText: 'Optional review',
                    ),
                    maxLines: 2,
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: _rating ? null : _rateDoctor,
                      child: _rating
                          ? const SizedBox(
                              height: 16,
                              width: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text('Submit Rating'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

StatusPillTone _severityTone(String severityLevel) {
  switch (severityLevel.toLowerCase()) {
    case 'critical':
      return StatusPillTone.error;
    case 'high':
      return StatusPillTone.warning;
    case 'medium':
      return StatusPillTone.info;
    default:
      return StatusPillTone.success;
  }
}
```

- [ ] **Step 2: Create `consultation_thread_screen.dart`**

Create `health_app/lib/screens/consultation/consultation_thread_screen.dart`:

```dart
import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../../models/models.dart';
import '../../providers/app_providers.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';

class ConsultationThreadScreen extends ConsumerStatefulWidget {
  const ConsultationThreadScreen({
    super.key,
    required this.ticket,
  });

  final ConsultationTicket ticket;

  @override
  ConsumerState<ConsultationThreadScreen> createState() => _ConsultationThreadScreenState();
}

class _ConsultationThreadScreenState extends ConsumerState<ConsultationThreadScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final List<ConsultationMessageItem> _messages = [];

  WebSocketChannel? _channel;
  StreamSubscription? _subscription;
  bool _loadingHistory = true;
  bool _sending = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadHistoryAndConnect();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    _channel?.sink.close();
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadHistoryAndConnect() async {
    setState(() {
      _loadingHistory = true;
      _error = null;
    });

    try {
      final history = await ApiClient.getConsultationMessages(widget.ticket.id);
      if (!mounted) return;
      setState(() {
        _messages
          ..clear()
          ..addAll(history);
        _loadingHistory = false;
      });
      _connect();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _loadingHistory = false;
        _error = e.toString();
      });
    }
  }

  void _connect() {
    final token = ApiClient.accessToken;
    if (token == null || token.isEmpty) {
      return;
    }

    try {
      _channel = ApiClient.consultationChannel(widget.ticket.id);
      _subscription = _channel?.stream.listen(
        (event) {
          final raw = event is String ? event : event.toString();
          final data = jsonDecode(raw) as Map<String, dynamic>;
          if (data['type'] != 'message') {
            return;
          }

          final incoming = ConsultationMessageItem.fromJson(data);
          if (!mounted) return;
          setState(() {
            _messages.add(incoming);
          });
          _scrollToBottom();
        },
        onError: (Object error) {
          if (!mounted) return;
          setState(() {
            _error = error.toString();
          });
        },
      );
    } catch (e) {
      setState(() {
        _error = e.toString();
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) {
        return;
      }
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  Future<void> _sendMessage() async {
    if (_messageController.text.trim().isEmpty || _sending) {
      return;
    }

    final text = _messageController.text.trim();
    _messageController.clear();

    setState(() {
      _sending = true;
    });

    try {
      _channel?.sink.add(jsonEncode({'message': text}));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not send message: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _sending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final currentUser = authState.user;

    return Scaffold(
      appBar: AppBar(
        title: Text('Consultation #${widget.ticket.id}'),
      ),
      body: Column(
        children: [
          Expanded(
            child: _loadingHistory
                ? const LoadingState(message: 'Loading consultation...')
                : _error != null
                    ? ErrorState(
                        message: _error!,
                        onRetry: _loadHistoryAndConnect,
                      )
                    : _messages.isEmpty
                        ? EmptyState(
                            title: 'No consultation messages yet',
                            message: 'Use the chat below to start the conversation.',
                            icon: Icons.chat_bubble_outline,
                          )
                        : ListView.builder(
                            controller: _scrollController,
                            padding: const EdgeInsets.all(16),
                            itemCount: _messages.length,
                            itemBuilder: (context, index) {
                              final item = _messages[index];
                              final isMine = currentUser != null && item.senderUserId == currentUser.id;
                              return Align(
                                alignment: isMine ? Alignment.centerRight : Alignment.centerLeft,
                                child: Container(
                                  margin: const EdgeInsets.only(bottom: 12),
                                  padding: const EdgeInsets.all(12),
                                  constraints: const BoxConstraints(maxWidth: 360),
                                  decoration: BoxDecoration(
                                    color: isMine ? Theme.of(context).colorScheme.primary : AppColors.grey100,
                                    borderRadius: BorderRadius.only(
                                      topLeft: const Radius.circular(18),
                                      topRight: const Radius.circular(18),
                                      bottomLeft: Radius.circular(isMine ? 18 : 4),
                                      bottomRight: Radius.circular(isMine ? 4 : 18),
                                    ),
                                  ),
                                  child: Text(
                                    item.message,
                                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                          color: isMine ? AppColors.white : null,
                                        ),
                                  ),
                                ),
                              );
                            },
                          ),
          ),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: AppColors.grey200)),
              color: AppColors.surface,
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: const InputDecoration(
                      hintText: 'Type a message...',
                    ),
                    textInputAction: TextInputAction.send,
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 12),
                ElevatedButton(
                  onPressed: _sending ? null : _sendMessage,
                  child: _sending
                      ? const SizedBox(
                          height: 16,
                          width: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('Send'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
```

- [ ] **Step 3: Update `doctor_navigation_screen.dart` to use `ConsultationScreen`**

In `health_app/lib/screens/doctor/doctor_navigation_screen.dart`, change line 9 from:

```dart
import '../consultation/consultation_chat_screen.dart';
```

to:

```dart
import '../consultation/consultation_screen.dart';
```

Then change both occurrences (line 35 and line 44) from:

```dart
                  builder: (_) => ConsultationChatScreen(ticket: ticket),
```

to:

```dart
                  builder: (_) => ConsultationScreen(ticket: ticket),
```

- [ ] **Step 4: Delete the old combined screen**

```bash
git rm health_app/lib/screens/consultation/consultation_chat_screen.dart
```

- [ ] **Step 5: Verify with `flutter analyze` and a manual doctor-flow run**

Run: `cd health_app && flutter analyze lib/screens/consultation lib/screens/doctor`
Expected: `No issues found!`

Then manually run the app (`flutter run`), log in as a doctor, and confirm:
- Opening a ticket from the dashboard's "Open now"/"My consultations" shortcuts and from the Consultations tab both land on `ConsultationScreen` showing the header pills and Accept/Close actions.
- Tapping "Open Chat" pushes `ConsultationThreadScreen`, where existing message history loads and a new message can be sent and appears in the thread.
- Closing a consultation and (as the patient login) submitting a rating still works.

- [ ] **Step 6: Commit**

```bash
git add health_app/lib/screens/consultation/consultation_screen.dart health_app/lib/screens/consultation/consultation_thread_screen.dart health_app/lib/screens/doctor/doctor_navigation_screen.dart
git commit -m "refactor: split ConsultationChatScreen into ConsultationScreen and ConsultationThreadScreen"
```

---

### Task 4: Frontend — inline "Consult a doctor" suggestion card in the AI chat screen

**Files:**
- Modify: `health_app/lib/screens/chat/chat_screen.dart`

**Interfaces:**
- Consumes: `ChatMessage.consultationSuggestion: ConsultationSuggestion?` (Task 2), `ConsultationScreen({required ConsultationTicket ticket})` (Task 3), `ApiClient.createManualConsultation({required String reason, String? categoryName}) -> Future<ConsultationTicket>` (already exists in `health_app/lib/services/api_client.dart:325-344`), `myConsultationsProvider` (already imported via `app_providers.dart`).
- Produces: nothing consumed by later tasks — this is the final task.

No automated test is added for this step: the project has no widget-test coverage for interactive flows beyond the placeholder `test/widget_test.dart`, and this UI is inherently interactive (network call + navigation) — Task 1/2's automated tests already cover the underlying data contract. Verification is `flutter analyze` plus the manual walkthrough in Step 6.

- [ ] **Step 1: Add imports and state fields**

In `health_app/lib/screens/chat/chat_screen.dart`, change the import block (lines 1-5) from:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../providers/app_providers.dart';
```

to:

```dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/models.dart';
import '../../services/api_client.dart';
import '../../theme/app_theme.dart';
import '../../widgets/common_widgets.dart';
import '../../providers/app_providers.dart';
import '../consultation/consultation_screen.dart';
```

Then, in `_ChatScreenState`, change the field declarations (lines 20-23) from:

```dart
  late TextEditingController _messageController;
  late ScrollController _scrollController;
  bool? _hasConsent;
  bool _isSending = false;
```

to:

```dart
  late TextEditingController _messageController;
  late ScrollController _scrollController;
  bool? _hasConsent;
  bool _isSending = false;
  ConsultationSuggestion? _activeSuggestion;
  bool _suggestionDismissed = false;
  bool _creatingConsultation = false;
```

- [ ] **Step 2: Capture the suggestion when a message is sent, and clear it when a new one is sent**

In `_sendMessage`, change:

```dart
    setState(() => _isSending = true);

    try {
      final sentMessage = await ref.read(sendMessageProvider(message).future);
      if (sentMessage.escalated && mounted) {
```

to:

```dart
    setState(() {
      _isSending = true;
      _activeSuggestion = null;
      _suggestionDismissed = false;
    });

    try {
      final sentMessage = await ref.read(sendMessageProvider(message).future);
      if (mounted) {
        setState(() {
          _activeSuggestion = sentMessage.consultationSuggestion;
        });
      }
      if (sentMessage.escalated && mounted) {
```

- [ ] **Step 3: Add the accept/dismiss handlers**

In `_ChatScreenState`, directly after the `_sendMessage` method (after its closing `}`, before `@override Widget build(...)`), add:

```dart
  Future<void> _acceptConsultationSuggestion(ConsultationSuggestion suggestion) async {
    setState(() => _creatingConsultation = true);
    try {
      final ticket = await ApiClient.createManualConsultation(
        reason: suggestion.reason,
        categoryName: suggestion.categoryName,
      );
      ref.invalidate(myConsultationsProvider);
      if (!mounted) return;
      setState(() => _activeSuggestion = null);
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => ConsultationScreen(ticket: ticket),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Could not start a consultation: $e')),
      );
    } finally {
      if (mounted) {
        setState(() => _creatingConsultation = false);
      }
    }
  }

  void _dismissConsultationSuggestion() {
    setState(() => _suggestionDismissed = true);
  }
```

- [ ] **Step 4: Render the card under the latest bot bubble**

In the `ListView.separated` `itemBuilder`, the returned `Column`'s `children` list currently ends with the AI response `Align(...)` (closing the list right after it, followed by `],\n                    );\n                  },`). Change the end of that `children` list from:

```dart
                        // AI response
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.only(right: 32),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppColors.grey100,
                              borderRadius: const BorderRadius.only(
                                topLeft: Radius.circular(18),
                                topRight: Radius.circular(18),
                                bottomLeft: Radius.circular(4),
                                bottomRight: Radius.circular(18),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  message.response,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                if (message.suggestedActions != null &&
                                    message.suggestedActions!.isNotEmpty) ...[
                                  const SizedBox(height: 12),
                                  Wrap(
                                    spacing: 8,
                                    children: message.suggestedActions!
                                        .map(
                                          (action) => ActionChip(
                                            label: Text(action),
                                            onPressed: () {
                                              _messageController.text = action;
                                              _sendMessage();
                                            },
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                );
```

to:

```dart
                        // AI response
                        Align(
                          alignment: Alignment.centerLeft,
                          child: Container(
                            margin: const EdgeInsets.only(right: 32),
                            padding: const EdgeInsets.all(14),
                            decoration: BoxDecoration(
                              color: AppColors.grey100,
                              borderRadius: const BorderRadius.only(
                                topLeft: Radius.circular(18),
                                topRight: Radius.circular(18),
                                bottomLeft: Radius.circular(4),
                                bottomRight: Radius.circular(18),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  message.response,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                if (message.suggestedActions != null &&
                                    message.suggestedActions!.isNotEmpty) ...[
                                  const SizedBox(height: 12),
                                  Wrap(
                                    spacing: 8,
                                    children: message.suggestedActions!
                                        .map(
                                          (action) => ActionChip(
                                            label: Text(action),
                                            onPressed: () {
                                              _messageController.text = action;
                                              _sendMessage();
                                            },
                                          ),
                                        )
                                        .toList(),
                                  ),
                                ],
                              ],
                            ),
                          ),
                        ),
                        if (index == sortedMessages.length - 1 &&
                            _activeSuggestion != null &&
                            !_suggestionDismissed) ...[
                          const SizedBox(height: 12),
                          Align(
                            alignment: Alignment.centerLeft,
                            child: Container(
                              margin: const EdgeInsets.only(right: 32),
                              padding: const EdgeInsets.all(14),
                              decoration: BoxDecoration(
                                color: AppColors.primaryLight,
                                borderRadius: BorderRadius.circular(14),
                                border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'This sounds like something worth discussing with a doctor.',
                                    style: Theme.of(context).textTheme.bodyMedium,
                                  ),
                                  const SizedBox(height: 10),
                                  Row(
                                    children: [
                                      ElevatedButton(
                                        onPressed: _creatingConsultation
                                            ? null
                                            : () => _acceptConsultationSuggestion(_activeSuggestion!),
                                        child: _creatingConsultation
                                            ? const SizedBox(
                                                height: 16,
                                                width: 16,
                                                child: CircularProgressIndicator(strokeWidth: 2),
                                              )
                                            : const Text('Consult a doctor'),
                                      ),
                                      const SizedBox(width: 8),
                                      TextButton(
                                        onPressed: _creatingConsultation ? null : _dismissConsultationSuggestion,
                                        child: const Text('Not now'),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ],
                    );
                  },
                );
```

- [ ] **Step 5: Verify with `flutter analyze`**

Run: `cd health_app && flutter analyze lib/screens/chat`
Expected: `No issues found!`

- [ ] **Step 6: Manual end-to-end verification**

Run `flutter run`, log in as a patient, grant chat consent, and:
- Send a medium-severity message (e.g. "I've been struggling with anxiety this week.") and confirm the "Consult a doctor" / "Not now" card appears under the bot's reply.
- Tap "Not now" — confirm the card disappears and no consultation is created (check the backend has no new row, or that no navigation occurs).
- Send another suggestion-triggering message, tap "Consult a doctor" — confirm it navigates into `ConsultationScreen` for a freshly created ticket, and that ticket also shows up for a doctor via the existing queue/dashboard.
- Send a message with no risk signal and confirm no card appears at all.

- [ ] **Step 7: Commit**

```bash
git add health_app/lib/screens/chat/chat_screen.dart
git commit -m "feat: show an inline consult-a-doctor suggestion in the AI chat"
```
