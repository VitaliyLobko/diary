# TODO — School Diary: анализ и план работ

> Аудит проекта от 2026-07-08 (backend / security / tests-CI / frontend).
> Чекбоксы — реальные задачи. Приоритет: 🔴 критично → 🟠 значимо → 🟡 tooling/tests → 🎨 frontend.
> Ссылки на файлы кликабельны из корня репозитория.

## Общая оценка
Архитектура (слои repo/service/route, web↔API split, RBAC, rate-limit, атомарный seed,
дисциплина инвалидации кэша) — заметно выше среднего для проекта такого размера.
Наибольшую ценность дают: развязка auth от жёсткой зависимости на Redis, снятие
блокирующих вызовов из async-хендлеров, недостающие индексы БД и валидация оценки.

---

## 🔴 Критичное (в первую очередь)

- [x] **Redis как единая точка отказа.** Доступ к кэшу инкапсулирован в `cache_get` /
  `cache_setex` / `cache_delete`: `RedisError` гасится и трактуется как промах → fallback
  на Postgres. Добавлены `socket_timeout`/`socket_connect_timeout` (0.5с, `REDIS_SOCKET_TIMEOUT`),
  `set`+`expire` заменён на атомарный `setex`.
  Файлы: src/services/cache.py, src/services/auth.py, src/routes/web/students.py, src/routes/api/v1/students.py
- [x] **Блокирующий код в async-хендлерах.** bcrypt и запросы к БД в `signup` и
  `refresh_access_token` вынесены в `run_in_threadpool` (оба хендлера остаются `async`,
  т.к. читают тело запроса).
  Файл: src/routes/auth.py
- [x] **Размер аплоада проверяется ПОСЛЕ чтения в память.** `_read_limited` читает чанками
  по 64КБ и отдаёт 413 сразу при превышении 5МБ (проверено: 500МБ-тело обрывается на 5.06МБ).
  Файл: src/services/uploads.py
- [x] **Нет валидации диапазона оценки.** `grade: int = Field(ge=1, le=12)`, `student_id`/
  `discipline_id` — `ge=1`. `dob` вынесен в общий тип `Dob` (не в будущем, не раньше 1900)
  и применён к студентам и учителям.
  Файлы: src/schemas/grades.py, src/schemas/common.py, src/schemas/students.py, src/schemas/teachers.py

## 🟠 Значимое (корректность)

- [x] **`create_user` теряет `body.email`.** Пишет `email=body.email`, Gravatar по email;
  проверка дубликата в `signup` тоже переведена на `body.email` (искала не в той колонке).
  Файлы: src/repository/users.py, src/routes/auth.py
- [x] **`grades` INNER-join с Teacher** → заменён на `outerjoin`: `Discipline.teacher_id`
  nullable, и оценки по дисциплине без учителя выпадали из списка и из счётчика пагинации.
  Файл: src/repository/grades.py
- [x] **`StudentModel.contacts` принимается API, но не сохраняется** → поле убрано из входной
  схемы (решение пользователя). Контакты остаются read-only в `StudentDetailResponse`.
  Файлы: src/schemas/students.py, src/repository/students.py
- [x] **`get_db` схлопывает все ошибки БД в 400 и течёт `str(err)`.** `IntegrityError`→409,
  прочее→500 с обобщённым detail (подробности только в лог). Добавлен `pool_pre_ping=True`.
  Файл: src/database/db.py
- [x] **Нет индексов на FK и `Contact.person_id`.** `index=True` на `students.group_id`,
  `grades.student_id`, `grades.discipline_id`, `disciplines.teacher_id`; составной
  `ix_contacts_person` через `__table_args__` (в БД они уже были из миграции e37117210965 —
  теперь их объявляют и модели, так что `create_all`/autogenerate не расходятся).
  `full_name` больше не падает на None: `btrim(coalesce(...) || ' ' || coalesce(...))` в SQL и
  эквивалент в Python. `concat_ws` не подошёл — он STABLE, Postgres отказывается его индексировать;
  trgm-индексы пересозданы на новом выражении (миграция a7c3e9d21b04), совпадение с запросом
  проверено через EXPLAIN.
  Файлы: src/database/models.py, migrations/versions/2026_07_10_1200-a7c3e9d21b04_*.py
- [x] **`main.js` хардкодит `http://localhost:8000/signup`** → относительный `/signup`.
  Файл: static/main.js
- [x] **Устаревший claim роли при refresh.** `/refresh` берёт роль из БД; middleware при
  silent-refresh зовёт новый `resolve_user_role` (кэш → БД) вместо claim'а из refresh-токена.
  Файлы: src/routes/auth.py, src/services/auth.py, main.py
- [x] **`/refresh` без rate-limit и без проверки `confirmed`.** Добавлен `REFRESH_LIMIT`
  (30/min) и отказ 401 неподтверждённому пользователю.
  Файлы: src/routes/auth.py, src/services/rate_limit.py

Регрессии на всё перечисленное: tests/test_correctness_regressions.py

## 🟠 Security (сверх корректности)

- [ ] **CORS `allow_origins=["*"]`** → заменить на явный список доверенных origin. main.py:40
- [ ] **Нет security-заголовков** (`X-Content-Type-Options: nosniff`, `X-Frame-Options`/CSP, HSTS).
  Добавить middleware. main.py:49
- [ ] **Аплоад не проверяется как реальное изображение** (спуфинг content-type); в паре с
  отсутствием nosniff — риск stored-XSS через /static/uploads. Валидировать байты (Pillow `verify()` + ре-энкод). src/services/uploads.py:37
- [ ] **Нет CSRF-токенов** на cookie-авторизованных мутациях (защита только на SameSite=Lax).
  Double-submit токен или fastapi-csrf-protect; токены и в нативные формы login/signup.
  Файлы: static/main.js:84,133,170,195,211,265; templates/base.html:125,151
- [ ] **Нет revocation токенов** — logout только удаляет cookie, выданные токены живут до истечения
  (refresh 7д). Добавить `jti` + Redis-denylist, проверять в `get_current_user`. src/services/auth.py:74; src/routes/auth.py:215
- [ ] **User enumeration на signup** (`409 "Account already exists"`) — раскрывает наличие email
  (на login защита есть). src/routes/auth.py:92
- [ ] **Слабая парольная политика** (`min_length=6`). Поднять до 12 + проверки. src/schemas/users.py:9
- [ ] **Redis без пароля/TLS**, а из него реконструируется user с ролями (RBAC). Изолировать сеть,
  `requirepass`+TLS в проде. src/services/cache.py:7
- [ ] **GET `/logout` CSRF-триггерится** (`<img src="/logout">`). Сделать POST. src/routes/auth.py:215
- [ ] **rate-limit по сырому client IP, in-memory** — за прокси все схлопываются в один бакет и
  сбрасывается по процессам. Trusted-proxy XFF + Redis-backend для slowapi. src/services/rate_limit.py:11
- [ ] **`set_user_role` без guard на самопонижение / последнего админа** — можно лишить всех прав. src/routes/auth.py:236

## 🟡 Тесты

- [ ] **Восстановить закомментированный позитивный тест `/login`** (валидный логин→токены,
  unconfirmed→401, неверный пароль→generic 401). tests/test_route_auth.py:99-153
- [ ] Покрыть `/login/web`, `/logout`, `/confirmed_email/{token}`, `/users/{email}/role`
  (admin-only: 403 для не-админа, 404 для неизвестного). src/routes/auth.py:134,215,254,231
- [ ] Добавить RBAC-тесты на **update/PATCH** (сейчас проверяются только create/delete).
- [ ] Позитивный CRUD для **groups / disciplines / grades** (сейчас только students/teachers),
  включая FK-null→404 ветки. src/repository/grades.py:11, disciplines.py:9
- [ ] `tests/test_unit_repository_users.py` (`create_user`, `confirmed_email`, `update_user_role`)
  на реальной сессии контейнера, не на моках.
- [ ] Заменить mock-chain юнит-тесты репозиториев на container-backed (как `TestAggregates`).
- [ ] **Изоляция**: убрать зависимость от порядка тестов (`scope="module"` + общая БД без rollback);
  транзакция/savepoint с откатом на каждый тест. tests/conftest.py:33-59

## 🟡 CI / tooling / packaging

- [ ] Порог покрытия: `--cov-fail-under=80` в CI + `fail_under` в pyproject. .github/workflows/ci.yml:26
- [ ] `ruff format --check .` и `pre-commit run --all-files` в CI. ci.yml:22
- [ ] Security-джоб: `pip-audit`/`safety`, `bandit -r src`, Trivy на образ. + `.github/dependabot.yml`.
- [ ] `alembic check` / `alembic upgrade head` в CI; smoke-тест собранного образа (curl /healthchecker); `concurrency:` для отмены устаревших ранов.
- [ ] Перенести `faker` из прод-requirements в dev. requirements.txt:19
- [ ] Объявить runtime-зависимости в `pyproject.toml [project.dependencies]` (сейчас истина только в requirements); рассмотреть lockfile.
- [ ] Рассмотреть уход с заброшенных `python-jose`/`passlib` на `pyjwt` + `bcrypt`/`argon2`.
- [ ] Добавить mypy/pyright (в проекте уже есть типы и SQLAlchemy 2.0 typed models).

## 🎨 Frontend / шаблоны

- [ ] **Починить сломанную разметку**: `students_with_grades.html` не закрывает `</main>` + 2 `</div>`;
  в `top_10_students.html` `id="modal-delete"/"modal-edit"` внутри цикла (дубли id) и мёртвые кнопки
  edit/delete без обработчиков; убрать backtick-литералы (base.html:147, top_10_students.html:22),
  `tabindex="-3"`→`-1`, битый `aria-labelledby="ModalLabel"`.
- [ ] **Вынести дублирование в макросы/инклюды**: `_detail_card.html`, `_confirm_modal.html`,
  list-scaffold (toolbar+table+create-modal). Карточки деталей и confirm-модалка скопированы ~5×.
- [ ] **`grades.html` поиск**: добавить `value=`, заменить фейковый «Clear»-submit на реальную ссылку
  `/grades/` (как в students/teachers). templates/grades.html:27-33
- [ ] **Убрать мусор из прода**: Lorem ipsum (teacher.html:42, top_10_students.html:20);
  русские `aria-label="Закрыть"`→«Close»; русские комментарии в style.css:110,114.
- [ ] **A11y/CSP**: убрать inline `onclick`/`onchange` (→ data-href + делегирование), клик-строки
  сделать доступными с клавиатуры (tabindex/role/ссылка), `aria-label` на иконки-кнопки,
  `<label>` на поля login/signup.
- [ ] Стандартизировать пути ассетов на абсолютные `/static/...` (или `url_for`), сейчас смесь `../static/...`.
- [ ] Нормализовать заголовки страниц (единое соглашение) в 6 web-роутах.

---

## Рекомендуемый порядок
1. **Сразу (безопасность/устойчивость):** Redis fallback+таймауты → разблокировать async signup/refresh
   → стриминговый лимит аплоада → `Field(ge=1,le=12)` → индексы на FK.
2. **Затем (корректность):** `create_user` → `body.email` → outer-join в grades → судьба `contacts`
   → маппинг ошибок в get_db → относительный URL в main.js.
3. **Полировка:** login-тесты + auth/update покрытие → порог покрытия и security-скан в CI
   → макросы шаблонов + починка sломанных страниц → CSRF + security-заголовки → убрать Lorem ipsum/разноязычие.

## Что хорошо (не трогать / сохранить как паттерн)
- Слоистая архитектура и web↔API split на общих функциях репозитория.
- JWT: пиннинг алгоритма, проверка scope, JSON-кэш вместо pickle.
- Seed с advisory-lock (закрыт TOCTOU), единая транзакция.
- Тесты на реальном Postgres (testcontainers), security-регрессии, smoke-рендер страниц.
- Дисциплина инвалидации кэша, консистентный счётчик пагинации.
- Тосты через `textContent`, autoescape вкл., `|safe`/`innerHTML` отсутствуют.
