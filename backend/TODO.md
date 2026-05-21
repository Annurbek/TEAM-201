# TODO — FastAPI Backendni To'liq Yakunlash Rejasi

Ushbu ro'yxat mavjud backendni to'liq ishlaydigan, testlangan va kengaytiriladigan holatga olib chiqish uchun yozilgan. Hozirgi kod bazada FastAPI + SQLAlchemy async ORM ishlatilmoqda, shuning uchun TODO ham shu stackga mos tuzildi.

## 1. Ustuvor Bosqichlar

### 1.1 Arxitektura va baza tayyorlash
- [ ] `app/main.py` dagi umumiy API prefixni yakuniy qarorga keltirish: `/api/v1` yoki `/api`.
- [ ] `app/core/config.py` dagi environment sozlamalarini tozalash va bir joyga jamlash.
- [ ] `app/db/database.py` ni production-safe qilish: engine, session, dependency, shutdown cleanup.
- [ ] `app/db/base.py` orqali barcha model importlarini to'liq ro'yxatlash.
- [ ] `alembic` migrationlarida model va schema sinxronligini tekshirish.
- [ ] `README.md` ni real ishga tushirish yo'riqnomasi bilan yangilash.

### 1.2 Autentifikatsiya va ruxsatlar
- [ ] JWT access token yaratish.
- [ ] Password hashing: bcrypt.
- [ ] `get_current_user` dependency.
- [ ] Role-based access control (`student`, `mentor`, `admin`).
- [ ] Disabled account tekshiruvlari.
- [ ] Token refresh kerak bo'lsa keyinroq qo'shish.

### 1.3 Business logic qatlamini tugatish
- [ ] `app/services/auth_service.py` ni to'liq yakunlash.
- [ ] `score_service.py` ni qayta hisoblash logikasi bilan to'ldirish.
- [ ] `ranking_service.py` ni leaderboard va sorting uchun yakunlash.
- [ ] `penalty_service.py` ni jarima/recovery oqimiga moslashtirish.
- [ ] Har bir mutating action uchun audit log yozish.

### 1.4 Schema va validatsiya
- [ ] `app/schemas/*` dagi request/response modellarini to'ldirish.
- [ ] FastAPI/Pydantic validation qo'llash.
- [ ] Common error response formatini bir xil qilish.
- [ ] Pagination, filtering, search uchun umumiy schema yaratish.

### 1.5 Testlar
- [ ] Auth smoke testlari.
- [ ] Har bir muhim endpoint uchun integration test.
- [ ] Score recalculation testlari.
- [ ] Role guard testlari.
- [ ] Duplicate entry va validation failure testlari.

---

## 2. Barcha Endpointlar Bo'yicha TODO

Quyidagi endpointlar `app/routers/*` ichida amalga oshirilishi kerak.

### 2.1 Auth

**Base:** `/api/v1/auth`

- [ ] `POST /login`  
  Login qilish. Body: `username/email + password`.  
  Natija: access token + user profile.

- [ ] `GET /me`  
  Hozirgi foydalanuvchi profilini qaytarish.

- [ ] `PUT /me`  
  O'z profilini yangilash: `full_name`, `phone`, `avatar_url`.

- [ ] `POST /change-password`  
  Joriy parolni tekshirib yangi parolga almashtirish.

- [ ] `POST /logout`  
  Client-side token bekor qilish uchun ixtiyoriy endpoint.

### 2.2 Users / Students / Mentors / Admins

**Base:** `/api/v1/users`

- [ ] `GET /`  
  Barcha userlarni list qilish. Filter: `role`, `search`, `is_active`.

- [ ] `GET /:id`  
  Bitta user profilini olish.

- [ ] `POST /`  
  Yangi user yaratish.

- [ ] `PUT /:id`  
  User ma'lumotlarini yangilash.

- [ ] `DELETE /:id`  
  Userni o'chirish yoki soft-delete qilish.

- [ ] `PUT /:id/toggle`  
  Userni aktiv/inaktiv qilish.

**Students uchun alohida base:** `/api/v1/students`

- [ ] `GET /`  
  Talabalar ro'yxati. Filter: `group`, `year`, `semester`, `search`.

- [ ] `GET /:id`  
  Talaba profili, score summary bilan.

- [ ] `GET /:id/score`  
  Joriy semestr score breakdown.

- [ ] `GET /:id/score/history`  
  Barcha semestrlar bo'yicha score history.

- [ ] `GET /:id/feed`  
  Talaba activity feed.

- [ ] `POST /:id/recalculate`  
  Talaba scoreini qayta hisoblash.

- [ ] `GET /leaderboard`  
  Public leaderboard. Filter: `group`, `year`, `semester`, pagination.

- [ ] `GET /leaderboard/guest`  
  Guest view: minimal ma'lumotlar.

### 2.3 Groups

**Base:** `/api/v1/groups`

- [ ] `GET /`  
  Barcha guruhlar ro'yxati.

- [ ] `GET /:id`  
  Bitta guruh ma'lumoti.

- [ ] `POST /`  
  Yangi guruh yaratish.

- [ ] `PUT /:id`  
  Guruh nomi / atributlarini yangilash.

- [ ] `DELETE /:id`  
  Guruhni o'chirish.

- [ ] `GET /:id/students`  
  Guruhdagi barcha talabalar.

### 2.4 Academic Years

**Base:** `/api/v1/academic-years`

- [ ] `GET /`  
  O'quv yillari ro'yxati.

- [ ] `GET /:id`  
  O'quv yili ma'lumoti.

- [ ] `POST /`  
  Yangi academic year yaratish.

- [ ] `PUT /:id`  
  Academic year yangilash.

- [ ] `PUT /:id/activate`  
  Faol yilda belgilash.

### 2.5 Semesters

**Base:** `/api/v1/semesters`

- [ ] `GET /`  
  Semestrlar ro'yxati.

- [ ] `GET /:id`  
  Bitta semestr ma'lumoti.

- [ ] `POST /`  
  Semestr yaratish.

- [ ] `PUT /:id`  
  Semestr yangilash.

- [ ] `PUT /:id/activate`  
  Hozirgi semestrni aktiv qilish.

### 2.6 Scores / Ranking

**Base:** `/api/v1/scores`

- [ ] `GET /:student_id`  
  Talabaning score breakdowni.

- [ ] `GET /:student_id/history`  
  Tarixiy score yozuvlari.

- [ ] `POST /:student_id/recalculate`  
  Scoreni qayta hisoblash.

- [ ] `GET /leaderboard`  
  Reyting ro'yxati.

- [ ] `GET /stats`  
  Umumiy score statistikalari.

**Base:** `/api/v1/ranking`

- [ ] `GET /`  
  Reytinglar ro'yxati.

- [ ] `GET /top`  
  Top studentlar.

- [ ] `GET /group/:group_id`  
  Guruh bo'yicha reyting.

### 2.7 Attendance

**Base:** `/api/v1/attendance`

- [ ] `POST /`  
  Bitta davomat yozuvi qo'shish.

- [ ] `POST /bulk`  
  Bulk attendance mark qilish.

- [ ] `GET /:student_id`  
  Talaba davomatlari.

- [ ] `GET /course/:course_id`  
  Fan bo'yicha davomat.

- [ ] `PUT /:id`  
  Davomatni tahrirlash.

- [ ] `DELETE /:id`  
  Davomatni o'chirish.

- [ ] `GET /stats/:student_id`  
  Davomat foizi va breakdown.

### 2.8 Grades

**Base:** `/api/v1/grades`

- [ ] `POST /`  
  Yangi baho qo'shish.

- [ ] `GET /:student_id`  
  Talabaning barcha baholari.

- [ ] `PUT /:id`  
  Baho tahriri.

- [ ] `DELETE /:id`  
  Bahoni o'chirish.

- [ ] `GET /stats/:student_id`  
  O'rtacha baho, foiz, fan bo'yicha statistikalar.

### 2.9 Achievements

**Base:** `/api/v1/achievements`

- [ ] `POST /`  
  Talaba yutuq yuklash. File upload qo'llab-quvvatlash.

- [ ] `GET /`  
  Admin uchun barcha achievements.

- [ ] `GET /my`  
  O'z achievements ro'yxati.

- [ ] `GET /:id`  
  Achievement detail.

- [ ] `PUT /:id/approve`  
  Approve qilish va ball belgilash.

- [ ] `PUT /:id/reject`  
  Reject qilish.

- [ ] `DELETE /:id`  
  Pending bo'lsa o'chirish.

### 2.10 Feedback

**Base:** `/api/v1/feedback`

- [ ] `POST /`  
  Mentor feedback yaratadi.

- [ ] `GET /student/:student_id`  
  Talaba uchun feedbacklar.

- [ ] `GET /my-given`  
  Mentor tomonidan berilgan feedbacklar.

- [ ] `PUT /:id`  
  Own feedbackni tahrirlash.

- [ ] `DELETE /:id`  
  Own feedbackni o'chirish.

### 2.11 Tutor Ratings

**Base:** `/api/v1/tutor-ratings`

- [ ] `POST /`  
  Mentor rating yaratadi yoki yangilaydi.

- [ ] `GET /:student_id`  
  Talaba ratinglari.

- [ ] `GET /semester/:semester/year/:year`  
  Semestr/yil bo'yicha ratinglar.

### 2.12 Penalties

**Base:** `/api/v1/penalties`

- [ ] `POST /`  
  Jarima kiritish.

- [ ] `GET /:student_id`  
  Talaba jarimalari.

- [ ] `PUT /:id`  
  Jarimani tahrirlash.

- [ ] `DELETE /:id`  
  Jarimani o'chirish.

### 2.13 Recovery Tasks

**Base:** `/api/v1/penalties/recovery`

- [ ] `POST /`  
  Recovery task biriktirish.

- [ ] `GET /:student_id`  
  Talaba recovery tasklari.

- [ ] `PUT /:id/complete`  
  Student taskni bajarganini belgilash.

- [ ] `PUT /:id/verify`  
  Admin/mentor tasdiqlaydi.

### 2.14 Employment

**Base:** `/api/v1/employment`

- [ ] `POST /`  
  Bandlik ma'lumotini yuborish.

- [ ] `GET /my`  
  Talabaning bandlik yozuvlari.

- [ ] `GET /`  
  Admin uchun barcha bandlik yozuvlari.

- [ ] `PUT /:id/verify`  
  Tasdiqlash va bonus ball berish.

- [ ] `DELETE /:id`  
  Bandlik yozuvini o'chirish.

### 2.15 Admin

**Base:** `/api/v1/admin`

- [ ] `GET /dashboard`  
  Umumiy statistikalar.

- [ ] `GET /audit-log`  
  Paginated audit log.

- [ ] `POST /users`  
  Admin user yaratadi.

- [ ] `PUT /users/:id/toggle`  
  User statusini o'zgartirish.

- [ ] `GET /reports/grant`  
  Grant eligibility report.

- [ ] `POST /recalculate-all`  
  Barcha talabalar scorelarini qayta hisoblash.

- [ ] `GET /notifications/send`  
  User(lar)ga notification yuborish.

- [ ] `GET /stats/groups`  
  Guruhlar bo'yicha KPI statistikasi.

- [ ] `GET /stats/roles`  
  Role bo'yicha user statistikasi.

### 2.16 Notifications

**Base:** `/api/v1/notifications`

- [ ] `GET /`  
  Hozirgi user notificationlari.

- [ ] `GET /unread-count`  
  O'qilmagan notificationlar soni.

- [ ] `PUT /:id/read`  
  Bitta notificationni o'qilgan qilish.

- [ ] `PUT /read-all`  
  Hammasini o'qilgan qilish.

- [ ] `DELETE /:id`  
  Notificationni o'chirish.

---

## 3. Muhim Cross-Cutting TODO

- [ ] Har bir write operation uchun `action_log` ga yozish.
- [ ] Har bir score-affecting eventdan keyin score recalculation trigger qilish.
- [ ] Permission checklarni router darajasida emas, dependency/service qatlamida ham tekshirish.
- [ ] Pagination, sorting, filtering uchun umumiy helperlar yozish.
- [ ] File uploadlar uchun `uploads/` papkasini yaratish.
- [ ] CSV export uchun alohida helper yozish.
- [ ] Error response formatini barcha endpointlarda bir xil qilish.
- [ ] Seed data skriptini idempotent qilish.
- [ ] Demo accountlarni README ga chiqarish.
- [ ] API docs uchun OpenAPI summary va response model yozish.

---

## 4. Score Calculation TODO

- [ ] Academic score hisoblash.
- [ ] Attendance score hisoblash.
- [ ] Practical skills score hisoblash.
- [ ] Achievement points cap tekshiruvi.
- [ ] Tutor rating aggregation.
- [ ] Discipline score va penalty deduction.
- [ ] Recovery points cap tekshiruvi.
- [ ] Employment bonus cap tekshiruvi.
- [ ] Grant eligibility rule.
- [ ] Score history yozish.
- [ ] Recalculate API orqali real-time qayta hisoblash.

---

## 5. Uzoqroq Bosqichlar

- [ ] WebSocket yoki server-sent events orqali real-time notification.
- [ ] Import/export uchun batch endpointlar.
- [ ] Soft delete strategiyasini yakunlash.
- [ ] Rate limiting va security hardening.
- [ ] Audit log uchun query optimizatsiyasi.
- [ ] Production deploy checklist.

---

## 6. Yakuniy Acceptance Criteria

- [ ] `pytest` yashil bo'ladi.
- [ ] Barcha asosiy endpointlar ishlaydi.
- [ ] JWT auth to'liq ishlaydi.
- [ ] Role-based access buzilmaydi.
- [ ] Score qayta hisoblash to'g'ri ishlaydi.
- [ ] Leaderboard va audit log to'g'ri qaytadi.
- [ ] Seed data bilan sistema demo holatda ishga tushadi.
