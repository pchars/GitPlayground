# Frontend: CSS и HTML

Как устроены стили и шаблоны GitPlayground. Источник визуальных решений — **[DESIGN.md](DESIGN.md)**.

## Загрузка стилей

`templates/core/base.html` подключает файлы в фиксированном порядке:

1. `static/css/common.css` — токены и общие примитивы
2. `{% block extra_css %}` — **один** page-specific файл
3. `static/css/responsive.css` — все `@media`-правила

Пример для лендинга:

```django
{% block extra_css %}
<link rel="stylesheet" href="{% static_v 'css/landing.css' %}">
{% endblock %}
```

## Cache-busting

Для CSS/JS используйте тег **`static_v`** вместо `static` — он автоматически
добавляет к URL хэш содержимого файла (`?v=<hash>`) и пересчитывает его при любом
изменении файла. Ручной бамп версии не нужен, и в шаблонах/репозитории нет
захардкоженных `?v=…design11`.

Тег объявлен в `apps/core/templatetags/static_versioned.py` и подключён как
`builtins` в `TEMPLATES` (см. `gitplayground/settings.py`), поэтому `{% load %}`
писать не нужно. Для внешних CDN-ссылок (например, xterm.js) тег не применяется.

## Карта CSS-файлов

| Файл | Назначение | Шаблон(ы) |
| --- | --- | --- |
| `common.css` | `:root`-токены, reset, типографика, header, footer, `.btn`, `.card`, формы, toasts | `base.html` (всегда) |
| `responsive.css` | Breakpoints mobile / tablet / desktop | `base.html` (всегда) |
| `landing.css` | Лендинг: hero, feature-band, слайдер, CTA | `core/landing.html` |
| `tasks.css` | Список задач, аккордеоны уровней | `core/tasks.html` |
| `playground.css` | Терминал, редактор файлов, валидация | `core/playground.html` |
| `theory.css` | Страница теории, Mermaid | `core/theory_detail.html` |
| `quiz.css` | Квиз: баблы сложности, варианты ответов | `quiz/home.html`, `quiz/play.html` |
| `profile.css` | Профиль, достижения | `core/profile.html` |
| `leaderboard.css` | Подиум, таблица | `core/leaderboard.html` |
| `auth.css` | Login, signup, password reset, activation | `core/login.html`, `core/signup*.html`, `core/password_reset*.html`, `core/activation*.html` |

Внешние стили: xterm.js CDN на странице плейграунда.

## Правила наследования

- **Токены** объявляются один раз в `:root` внутри `common.css` и соответствуют именам из `docs/DESIGN.md` (`--color-primary`, `--spacing-lg`, `--rounded-md`, …).
- **Страничные файлы** используют только `var(--…)`; не дублируют reset, кнопки и карточки.
- **Адаптив** — только в `responsive.css`; в page CSS и `common.css` media queries не добавлять.
- **Одна страница — один CSS**: не складывайте стили нескольких экранов в один файл (исключение — `quiz.css` для home + play, т.к. это один модуль).

## HTML-шаблоны

- Базовый layout: `templates/core/base.html`
- Контент страницы: `{% block content %}`
- Скрипты страницы — в конце `{% block content %}`, после разметки
- Пользовательский текст — на русском; имена классов и файлов — на английском

### Семантика из docs/DESIGN.md

| Класс / блок | Где используется |
| --- | --- |
| `.header.top-nav` | Шапка всех страниц |
| `.site-footer` | Тёмный подвал |
| `.landing-hero`, `.feature-band-item` | Лендинг |
| `.card`, `.card-surface` | Карточки контента |
| `.btn-primary`, `.btn-secondary`, `.btn-text-link` | Кнопки |
| `.nav-pill-group` | Группы переключателей (квиз) |
| `.product-mockup-card` | Терминал / UI продукта в плейграунде |

## JavaScript

| Файл | Страница |
| --- | --- |
| `toast.js`, `scroll_top.js`, `nav_mobile.js` | Все страницы (`base.html`, через `static_v`) |
| `auth.js` | Login / signup / password reset confirm |
| `landing_slider.js` | Лендинг |
| `playground.js`, `terminal_paste.js` | Плейграунд |

Правила paste в терминале должны совпадать на клиенте (`terminal_paste.js`) и сервере (`apps/core/terminal_paste.py`).

## JSON API плейграунда

Страница плейграунда — HTML (`GET /playground/<task_id>/`). Терминал и редактор вызывают JSON-эндпоинты (только для авторизованных пользователей, CSRF на POST):

| Метод | URL | Назначение |
| --- | --- | --- |
| POST | `/playground/<task_id>/run/` | Выполнить одну команду (allowlist) |
| POST | `/playground/<task_id>/file/read/` | Прочитать файл из workspace |
| POST | `/playground/<task_id>/file/write/` | Записать файл (многострочный текст) |
| POST | `/playground/<task_id>/validate/` | Запустить `validator.py`, вернуть вердикт |
| POST | `/playground/<task_id>/reset/` | Сбросить сессию песочницы |
| POST | `/playground/<task_id>/hint/` | Разблокировать подсказку |

- `task_id` в URL — route-id с подчёркиваниями (`gh_1_1`), не `external_id` с точками (`gh.1.1`).
- Реализация: `apps/core/views/playground.py`, маршруты — `apps/core/urls.py`.
- Клиент: `static/js/playground.js`.
- Общий формат ошибки: `{ "ok": false, "message": "…" }`.

Отдельный OpenAPI-файл не ведётся: контракт живёт в коде и JS; при изменении API обновляйте view, фронт и тесты в одном PR.

## Breakpoints

| Имя | Ширина | Файл |
| --- | --- | --- |
| Mobile | `< 768px` | `responsive.css` — hamburger-навигация, 1-колоночные сетки |
| Tablet | `768–1024px` | `responsive.css` — 2-колоночный footer/features, плейграунд с вкладками |
| Desktop | `1024–1440px` | `responsive.css` |
| Wide | `> 1440px` | `responsive.css` |

Подробности коллапса сеток — в разделе Responsive Behavior в `docs/DESIGN.md`.
