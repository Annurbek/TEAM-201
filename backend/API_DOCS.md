# Edumetric API Documentation

Base URL: `http://localhost:8000/api`
All endpoints require `Authorization: Bearer <token>` header unless marked as **Public**.

---

## Authentication

### POST `/api/auth/login`
Login and receive access token.

**Request Body:**
```json
{
  "username": "admin@pdp.uz",
  "password": "DemoPass123!"
}
```

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

**Error 401:**
```json
{ "success": false, "message": "Unauthorized", "detail": "Invalid credentials" }
```

---

### GET `/api/auth/me`
Get current user profile.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "id": 1,
  "full_name": "PDP Admin",
  "username": "admin@pdp.uz",
  "phone": "+998901111111",
  "role": "admin",
  "is_active": true,
  "created_at": "2025-09-01T00:00:00",
  "updated_at": "2025-09-01T00:00:00",
  "last_login": "2025-09-01T00:00:00"
}
```

---

### PUT `/api/auth/me`
Update current user profile.

**Request Body:**
```json
{
  "full_name": "New Name",
  "phone": "+998901234567",
  "avatar_url": "https://..."
}
```
All fields optional.

**Response 200:** Same as GET `/api/auth/me`

---

### POST `/api/auth/change-password`
Change current user password.

**Request Body:**
```json
{
  "current_password": "DemoPass123!",
  "new_password": "NewPass456!"
}
```

**Response 200:**
```json
{ "success": true, "message": "Password changed", "detail": null }
```

---

## Students

### GET `/api/students`
List all students (admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Params:**
| Param | Type | Default | Description |
|---|---|---|---|
| search | string | - | Search by name, username, or student_code |
| group_id | int | - | Filter by group |
| page | int | 1 | Page number (min 1) |
| size | int | 20 | Page size (1-100) |

**Response 200:**
```json
{
  "items": [
    {
      "student_id": 1,
      "id": 2,
      "full_name": "Student 01",
      "username": "student01@pdp.uz",
      "phone": "+998910000001",
      "role": "student",
      "is_active": true,
      "created_at": "...",
      "updated_at": "...",
      "last_login": null,
      "student_code": "PDP-2025-001",
      "current_group_id": 1,
      "admission_year": 2025
    }
  ],
  "page": 1,
  "size": 20,
  "total": 20
}
```

---

### GET `/api/students/{student_id}`
Get student detail with current score.

**Headers:** `Authorization: Bearer <token>`

**Access Rules:**
- Admin/Super Admin: all students
- Tutor: students in their groups
- Parent: their linked children
- Student: own profile only

**Response 200:**
```json
{
  "student": {
    "student_id": 1,
    "id": 2,
    "full_name": "Student 01",
    "username": "student01@pdp.uz",
    "phone": "+998910000001",
    "role": "student",
    "is_active": true,
    "created_at": "...",
    "updated_at": "...",
    "last_login": null,
    "student_code": "PDP-2025-001",
    "current_group_id": 1,
    "admission_year": 2025
  },
  "score": {
    "student_id": 1,
    "semester_id": 1,
    "academic_year_id": 1,
    "academic_score": 32.5,
    "academic_percentage": 81.25,
    "attendance_score": 18.0,
    "attendance_percentage": 90.0,
    "practical_score": 12.0,
    "activity_score": 5.0,
    "tutor_score": 4.2,
    "discipline_score": 9.0,
    "penalty_points": -3.0,
    "recovery_points": 2.0,
    "employment_bonus": 5.0,
    "base_total": 80.7,
    "final_score": 84.7,
    "grant_eligible": true,
    "snapshot_id": 1
  }
}
```

---

### GET `/api/students/{student_id}/score`
Get student score breakdown.

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same score object as above.

---

### GET `/api/students/{student_id}/score/history`
Get student score history (ranking snapshots).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "snapshot_id": 1,
      "semester_id": 1,
      "academic_year_id": 1,
      "academic_year": "2025-2026",
      "semester": 1,
      "academic_points": 32.5,
      "attendance_points": 18.0,
      "certificate_points": 5.0,
      "project_points": 12.0,
      "discipline_points": 9.0,
      "tutor_points": 4.2,
      "work_points": 5.0,
      "penalty_points": -1.0,
      "total_points": 84.7,
      "rank_position": 3,
      "calculated_at": "2025-09-15T10:30:00"
    }
  ]
}
```

---

### GET `/api/students/{student_id}/feed`
Get student activity feed (all events combined).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    { "type": "grade", "created_at": "2025-09-15T10:00:00", "data": { ... } },
    { "type": "attendance", "created_at": "2025-09-14T09:00:00", "data": { ... } },
    { "type": "achievement", "created_at": "2025-09-10T14:00:00", "data": { ... } },
    { "type": "feedback", "created_at": "2025-09-08T11:00:00", "data": { ... } },
    { "type": "penalty", "created_at": "2025-09-05T16:00:00", "data": { ... } },
    { "type": "recovery", "created_at": "2025-09-01T08:00:00", "data": { ... } },
    { "type": "score_history", "created_at": "2025-09-15T10:30:00", "data": { ... } }
  ]
}
```

---

### POST `/api/students/{student_id}/recalculate`
Recalculate student score (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same score object.

---

## Attendance

### GET `/api/attendance/{student_id}`
List attendance records for a student.

**Headers:** `Authorization: Bearer <token>`

**Query Params:**
| Param | Type | Default | Description |
|---|---|---|---|
| course_id | int | - | Filter by course |
| date_from | string | - | Start date (YYYY-MM-DD) |
| date_to | string | - | End date (YYYY-MM-DD) |

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "student_id": 1,
      "course_id": 1,
      "semester_id": 1,
      "date": "2025-09-01",
      "status": "present",
      "recorded_by_id": 2,
      "note": null,
      "created_at": "2025-09-01T09:00:00"
    }
  ]
}
```

**Attendance Status values:** `present`, `absent`, `late`, `excused`

---

### GET `/api/attendance/course/{course_id}`
List attendance for a course (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same as above, all students in the course.

---

### GET `/api/attendance/stats/{student_id}`
Get attendance statistics for current semester.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "percent": 90.0, "points": 18.0 }
```

---

### POST `/api/attendance`
Create attendance record (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "student_id": 1,
  "course_id": 1,
  "semester_id": 1,
  "date": "2025-09-15",
  "status": "present",
  "note": null
}
```

**Response 200:**
```json
{ "id": 123, "message": "Attendance recorded" }
```

---

### POST `/api/attendance/bulk`
Create multiple attendance records (tutor/admin only).

**Request Body:**
```json
{
  "course_id": 1,
  "semester_id": 1,
  "date": "2025-09-15",
  "records": [
    { "student_id": 1, "status": "present" },
    { "student_id": 2, "status": "absent" },
    { "student_id": 3, "status": "late" }
  ]
}
```

**Response 200:**
```json
{ "created": [123, 124, 125] }
```

---

### PUT `/api/attendance/{attendance_id}`
Update attendance record (tutor/admin only).

**Request Body:** Same as POST `/api/attendance`

**Response 200:**
```json
{ "message": "Attendance updated" }
```

---

## Grades

### POST `/api/grades`
Create grade record (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "student_id": 1,
  "course_id": 1,
  "semester_id": 1,
  "assignment_name": "Midterm Exam",
  "score": 85.0,
  "max_score": 100.0,
  "submission_date": "2025-09-15",
  "deadline": "2025-09-17",
  "is_late": false,
  "quality": "excellent",
  "is_independent": true
}
```

**Quality values:** `excellent`, `good`, `satisfactory`, `poor`, `plagiarized`

**Response 200:**
```json
{ "id": 456, "message": "Grade recorded" }
```

---

### GET `/api/grades/{student_id}`
List grades for a student.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 456,
      "student_id": 1,
      "course_id": 1,
      "semester_id": 1,
      "assignment_name": "Midterm Exam",
      "score": 85.0,
      "max_score": 100.0,
      "submission_date": "2025-09-15",
      "deadline": "2025-09-17",
      "is_late": false,
      "quality": "excellent",
      "is_independent": true,
      "graded_by_id": 2,
      "created_at": "2025-09-15T10:00:00"
    }
  ]
}
```

---

### PUT `/api/grades/{grade_id}`
Update grade (tutor/admin only).

**Request Body:** (all fields optional)
```json
{
  "score": 90.0,
  "quality": "good"
}
```

**Response 200:**
```json
{ "message": "Grade updated" }
```

---

### DELETE `/api/grades/{grade_id}`
Delete grade (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "message": "Grade deleted" }
```

---

### GET `/api/grades/stats/{student_id}`
Get grade statistics (average percentage).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "average_percentage": 82.5 }
```

---

## Achievements

### POST `/api/achievements`
Submit achievement (student/admin only).

**Content-Type:** `multipart/form-data`

**Form Fields:**
| Field | Type | Required | Description |
|---|---|---|---|
| type | string | Yes | Achievement type (see below) |
| title | string | Yes | Achievement title |
| description | string | No | Description |
| points_claimed | number | Yes | Points claimed |
| semester_id | number | No | Semester ID |
| document | file | No | Supporting document |

**Achievement Types:**
`hackathon_participant`, `hackathon_winner`, `startup`, `mentoring`, `certificate_online`, `certificate_offline`, `certificate_national_it`, `certificate_language`, `certificate_international`, `volunteering`, `soft_skills`, `networking`, `project_participant`, `direction_assistant`, `strategic_assistant`

**Response 200:**
```json
{ "id": 789, "message": "Achievement submitted" }
```

---

### GET `/api/achievements`
List all achievements (admin only).

**Query Params:** `status_filter`, `type_filter`, `student_id`

**Response 200:**
```json
{
  "items": [
    {
      "id": 789,
      "student_id": 1,
      "semester_id": 1,
      "type": "hackathon_participant",
      "title": "Hackathon Participant",
      "description": "...",
      "document_url": "/uploads/achievements/...",
      "points_claimed": 1.0,
      "points_approved": 1.0,
      "status": "approved",
      "admin_note": "Approved",
      "submitted_at": "2025-09-10T14:00:00",
      "reviewed_at": "2025-09-11T10:00:00",
      "reviewed_by_id": 1
    }
  ]
}
```

---

### GET `/api/achievements/my`
Get current user's achievements.

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same items structure.

---

### GET `/api/achievements/{achievement_id}`
Get achievement detail.

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Single achievement object.

---

### PUT `/api/achievements/{achievement_id}/approve`
Approve achievement (admin only).

**Request Body:**
```json
{
  "points_approved": 1.0,
  "admin_note": "Verified and approved"
}
```

**Response 200:**
```json
{ "message": "Achievement approved" }
```

---

### PUT `/api/achievements/{achievement_id}/reject`
Reject achievement (admin only).

**Request Body:**
```json
{
  "points_approved": null,
  "admin_note": "Insufficient evidence"
}
```

**Response 200:**
```json
{ "message": "Achievement rejected" }
```

---

### DELETE `/api/achievements/{achievement_id}`
Delete achievement.

**Headers:** `Authorization: Bearer <token>`

Students can only delete their own pending achievements.

**Response 200:**
```json
{ "message": "Achievement deleted" }
```

---

## Feedback

### POST `/api/feedback`
Create feedback (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "student_id": 1,
  "course_id": 1,
  "type": "academic",
  "content": "Great progress in coursework!",
  "sentiment": "positive",
  "is_visible_to_student": true
}
```

**Type values:** `academic`, `behavioral`, `project`, `general`
**Sentiment values:** `positive`, `neutral`, `negative`

**Response 200:**
```json
{ "id": 101, "message": "Feedback created" }
```

---

### GET `/api/feedback/student/{student_id}`
Get feedback for a student.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 101,
      "mentor_id": 2,
      "student_id": 1,
      "semester_id": 1,
      "course_id": 1,
      "type": "academic",
      "content": "Great progress!",
      "sentiment": "positive",
      "is_visible_to_student": true,
      "created_at": "2025-09-15T10:00:00"
    }
  ]
}
```

---

### GET `/api/feedback/my-given`
Get feedback given by current tutor.

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same items structure.

---

### PUT `/api/feedback/{feedback_id}`
Update feedback (tutor/admin only).

**Request Body:**
```json
{
  "content": "Updated feedback text",
  "sentiment": "neutral",
  "is_visible_to_student": false
}
```

**Response 200:**
```json
{ "message": "Feedback updated" }
```

---

### DELETE `/api/feedback/{feedback_id}`
Delete feedback (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "message": "Feedback deleted" }
```

---

## Tutor Ratings

### POST `/api/tutor-ratings`
Create or update tutor rating (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "student_id": 1,
  "semester": 1,
  "year": 1,
  "corporate_culture": 0.8,
  "social_activity": 0.9,
  "soft_skills": 0.7,
  "discipline": 0.8,
  "dorm_activity": 0.6,
  "note": "Good overall performance"
}
```

Each sub-score: 0.0 - 1.0. Total is auto-calculated (max 5.0).

**Response 200:**
```json
{ "id": 201, "total": 3.8 }
```

---

### GET `/api/tutor-ratings/{student_id}`
Get tutor ratings for a student.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 201,
      "mentor_id": 2,
      "student_id": 1,
      "semester": 1,
      "year": 1,
      "corporate_culture": 0.8,
      "social_activity": 0.9,
      "soft_skills": 0.7,
      "discipline": 0.8,
      "dorm_activity": 0.6,
      "total": 3.8,
      "note": "Good overall performance",
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

---

## Penalties & Recovery

### POST `/api/penalties`
Create penalty (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "student_id": 1,
  "type": "Late submission",
  "reason": "Assignment submitted past deadline",
  "points": 3.0,
  "semester_id": 1
}
```

**Response 200:**
```json
{ "id": 301, "message": "Penalty created" }
```

---

### GET `/api/penalties/{student_id}`
List penalties for a student.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 301,
      "student_id": 1,
      "semester_id": 1,
      "amount": -3,
      "covered_amount": 0,
      "comment": "Late submission: Assignment submitted past deadline",
      "status": "active",
      "created_by_id": 1,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

**Penalty Status values:** `active`, `partially_covered`, `covered`

---

### POST `/api/penalties/recovery`
Create recovery task (tutor/admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "student_id": 1,
  "task_description": "Support class cleanup and mentoring",
  "points_recoverable": 2.0,
  "semester_id": 1,
  "due_date": "2025-11-01"
}
```

**Response 200:**
```json
{ "id": 401, "message": "Recovery task created" }
```

---

### PUT `/api/penalties/recovery/{task_id}/complete`
Mark recovery task as complete (student/admin).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "message": "Recovery task marked complete" }
```

---

### PUT `/api/penalties/recovery/{task_id}/verify`
Verify recovery task and award points (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{ "points_recovered": 2.0 }
```

**Response 200:**
```json
{ "message": "Recovery task verified" }
```

---

## Employment

### POST `/api/employment`
Submit employment record (student/admin only).

**Content-Type:** `multipart/form-data`

**Form Fields:**
| Field | Type | Required |
|---|---|---|
| student_id | number | No (auto for students) |
| company_name | string | Yes |
| position | string | Yes |
| type | string | Yes |
| hours_per_week | number | No |
| start_date | string | Yes |
| end_date | string | No |
| is_it_related | boolean | No (default true) |
| bonus_points | number | No (default 0) |
| semester_id | number | No |
| semester | number | Yes |
| year | number | Yes |
| document | file | No |

**Type values:** `freelance`, `part_time`, `full_time`

**Response 200:**
```json
{ "id": 501, "message": "Employment submitted" }
```

---

### GET `/api/employment/my`
Get current user's employment records.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 501,
      "student_id": 1,
      "company_name": "Uzum Tech",
      "position": "Junior Developer",
      "type": "part_time",
      "hours_per_week": 20,
      "start_date": "2025-10-01",
      "end_date": null,
      "is_it_related": true,
      "bonus_points": 5.0,
      "verified": false,
      "document_url": null,
      "semester_id": 1,
      "semester": 1,
      "year": 2025,
      "created_at": "..."
    }
  ]
}
```

---

### GET `/api/employment`
List all employment records (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same items structure.

---

### PUT `/api/employment/{employment_id}/verify`
Verify employment record (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{ "bonus_points": 5.0 }
```

**Response 200:**
```json
{ "message": "Employment verified" }
```

---

## Leaderboard

### GET `/api/students/leaderboard/guest`
Public leaderboard (no auth required).

**Query Params:** `page` (default 1), `size` (default 20, max 100)

**Response 200:**
```json
{
  "items": [
    {
      "rank": 1,
      "student_id": 1,
      "student_code": "PDP-2025-001",
      "total_points": 95.5,
      "academic_points": 38.0,
      "attendance_points": 19.0,
      "project_points": 12.0,
      "certificate_points": 5.0,
      "discipline_points": 10.0,
      "tutor_points": 4.5,
      "work_points": 7.0,
      "penalty_points": 0.0
    }
  ],
  "page": 1,
  "size": 20,
  "total": 20,
  "academic_year_id": 1
}
```

---

### GET `/api/students/leaderboard`
Leaderboard (authenticated).

**Query Params:** `page`, `size`, `academic_year_id`

**Response 200:** Same as guest leaderboard.

---

## Admin

### GET `/api/admin/dashboard`
Admin dashboard statistics.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "total_students": 20,
  "grant_eligible": 12,
  "average_score": 78.5
}
```

---

### GET `/api/admin/audit-log`
View audit log.

**Headers:** `Authorization: Bearer <token>`

**Query Params:** `page` (default 1), `size` (default 20, max 100)

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "actor_id": 1,
      "action": "create",
      "model_name": "User",
      "record_id": 5,
      "request_path": "/admin/users",
      "request_method": "POST",
      "old_data": null,
      "new_data": "{...}",
      "created_at": "..."
    }
  ],
  "page": 1,
  "size": 20,
  "total": 150
}
```

---

### POST `/api/admin/users`
Create user (admin provisions accounts).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "full_name": "New Student",
  "username": "newstudent@pdp.uz",
  "password": "SecurePass123!",
  "role": "student",
  "phone": "+998909876543",
  "student_code": "PDP-2025-021",
  "current_group_id": 1,
  "admission_year": 2025
}
```

**Role values:** `super_admin`, `admin`, `tutor`, `parent`, `student`

**Response 200:**
```json
{
  "id": 35,
  "full_name": "New Student",
  "username": "newstudent@pdp.uz",
  "phone": "+998909876543",
  "role": "student",
  "is_active": true,
  "created_at": "...",
  "updated_at": "...",
  "last_login": null,
  "generated_password": "SecurePass123!",
  "generated_username": "newstudent@pdp.uz"
}
```

---

### PUT `/api/admin/users/{user_id}/toggle`
Toggle user active/inactive.

**Headers:** `Authorization: Bearer <token>`

**Response 200:** User object with updated `is_active`.

---

### GET `/api/admin/reports/grant`
Grant eligibility report.

**Headers:** `Authorization: Bearer <token>`

**Response 200:** Same as leaderboard with grant data.

---

### POST `/api/admin/recalculate-all`
Recalculate all student scores.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "recalculated": 20 }
```

---

### POST `/api/admin/notifications/send`
Send notification to a user.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "user_id": 2,
  "title": "Important Notice",
  "message": "Your account has been updated.",
  "type": "info"
}
```

**Type values:** `info`, `warning`, `success`, `danger`

**Response 200:**
```json
{ "id": 1, "message": "Notification sent" }
```

---

## Users

### GET `/api/users`
List users (admin only).

**Headers:** `Authorization: Bearer <token>`

**Query Params:** `role`, `search`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "full_name": "PDP Admin",
      "username": "admin@pdp.uz",
      "phone": "+998901111111",
      "role": "admin",
      "is_active": true,
      "created_at": "...",
      "updated_at": "...",
      "last_login": "..."
    }
  ]
}
```

---

### GET `/api/users/{user_id}`
Get user detail.

**Headers:** `Authorization: Bearer <token>`

Admins can view any user. Other users can only view themselves.

**Response 200:** Same user object.

---

### PUT `/api/users/{user_id}`
Update user.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "full_name": "Updated Name",
  "phone": "+998901234567",
  "is_active": true
}
```

**Response 200:** Updated user object.

---

### DELETE `/api/users/{user_id}`
Delete user (admin only).

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{ "message": "User deleted" }
```

---

## Groups

### GET `/api/groups`
List all groups.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "CS-101",
      "course": 1,
      "academic_year_id": 1,
      "created_at": "..."
    }
  ]
}
```

---

### POST `/api/groups`
Create group (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "CS-103",
  "course": 1,
  "academic_year_id": 1
}
```

**Response 200:**
```json
{ "id": 3, "message": "Group created" }
```

---

## Courses

### GET `/api/courses`
List all courses.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Programming",
      "code": "PROGRAMMING",
      "mentor_id": 2,
      "year": 1,
      "semester": 1,
      "max_hours": 80,
      "is_active": true,
      "created_at": "..."
    }
  ]
}
```

---

### POST `/api/courses`
Create course (admin/tutor only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Machine Learning",
  "code": "ML-101",
  "mentor_id": 2,
  "year": 1,
  "semester": 1,
  "max_hours": 80
}
```

**Response 200:**
```json
{ "id": 7, "message": "Course created" }
```

---

## Academic Years

### GET `/api/academic-years`
List academic years.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "name": "2025-2026",
      "start_date": "2025-09-01T00:00:00",
      "end_date": "2026-06-30T00:00:00",
      "is_current": true,
      "created_at": "..."
    }
  ]
}
```

---

### POST `/api/academic-years`
Create academic year (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "2026-2027",
  "start_date": "2026-09-01T00:00:00",
  "end_date": "2027-06-30T00:00:00",
  "is_current": false
}
```

**Response 200:**
```json
{ "id": 2, "message": "Academic year created" }
```

---

### PUT `/api/academic-years/{academic_year_id}`
Update academic year (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:** Same as POST.

**Response 200:**
```json
{ "message": "Academic year updated" }
```

---

## Semesters

### GET `/api/semesters`
List semesters.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "items": [
    {
      "id": 1,
      "academic_year_id": 1,
      "number": 1,
      "start_date": "2025-09-01T00:00:00",
      "end_date": "2026-01-31T00:00:00",
      "is_current": true,
      "created_at": "..."
    }
  ]
}
```

---

### POST `/api/semesters`
Create semester (admin only).

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "academic_year_id": 1,
  "number": 2,
  "start_date": "2026-02-01T00:00:00",
  "end_date": "2026-06-30T00:00:00",
  "is_current": false
}
```

**Response 200:**
```json
{ "id": 2, "message": "Semester created" }
```

---

## Parent

### GET `/api/parent/children`
Get parent's linked children.

**Headers:** `Authorization: Bearer <token>` (role: parent)

**Response 200:**
```json
{
  "items": [
    {
      "student_id": 1,
      "full_name": "Student 01",
      "username": "student01@pdp.uz",
      "student_code": "PDP-2025-001",
      "current_group_id": 1,
      "current_group_name": "CS-101",
      "admission_year": 2025,
      "is_active": true
    }
  ]
}
```

---

### GET `/api/parent/children/{student_id}/ranks`
Get child's ranking details.

**Headers:** `Authorization: Bearer <token>` (role: parent)

**Query Params:** `academic_year_id` (optional)

**Response 200:**
```json
{
  "student_id": 1,
  "overall_rank": 3,
  "overall_points": 84.7,
  "university_total": 20,
  "group_rank": 1,
  "group_total": 10,
  "course_rank": 2,
  "course_total": 10
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "success": false,
  "message": "Unauthorized" | "Permission denied" | "Error" | "Validation error",
  "detail": "Specific error message"
}
```

| Status | Meaning |
|---|---|
| 401 | Missing/invalid token, user not found |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 422 | Validation error (invalid request body) |
| 500 | Internal server error |

---

## Scoring Model

| Component | Max Points |
|---|---|
| Academic (grades) | 40 |
| Attendance | 20 |
| Practical skills | 15 |
| Activity / certificates | 10 |
| Tutor rating | 5 |
| Discipline | 10 |
| Penalty (negative) | -20 |
| Recovery (positive) | +10 |
| Employment bonus | +10 |
| **Total (capped)** | **120** |

**Grant eligibility:** `final_score >= 80 AND academic_percentage >= 80`

---

## Demo Credentials

All users share the same password: `DemoPass123!`

| Role | Email |
|---|---|
| Admin | `admin@pdp.uz` |
| Mentor 1 | `mentor1@pdp.uz` |
| Mentor 2 | `mentor2@pdp.uz` |
| Mentor 3 | `mentor3@pdp.uz` |
| Students | `student01@pdp.uz` ... `student20@pdp.uz` |
| Parents | `parent01@pdp.uz` ... `parent10@pdp.uz` |
