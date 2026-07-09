# Frontend: CSS и HTML

Как устроены стили и шаблоны GitPlayground. Источник визуальных решений — **[DESIGN.md](../DESIGN.md)**.

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

- **Токены** объявляются один раз в `:root` внутри `common.css` и соответствуют именам из `DESIGN.md` (`--color-primary`, `--spacing-lg`, `--rounded-md`, …).
- **Страничные файлы** используют только `var(--…)`; не дублируют reset, кнопки и карточки.
- **Адаптив** — только в `responsive.css`; в page CSS и `common.css` media queries не добавлять.
- **Одна страница — один CSS**: не складывайте стили нескольких экранов в один файл (исключение — `quiz.css` для home + play, т.к. это один модуль).

## HTML-шаблоны

- Базовый layout: `templates/core/base.html`
- Контент страницы: `{% block content %}`
- Скрипты страницы — в конце `{% block content %}`, после разметки
- Пользовательский текст — на русском; имена классов и файлов — на английском

### Семантика из DESIGN.md

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
| `toast.js`, `scroll_top.js`, `auth.js`, `landing_slider.js` | Все (из `base.html` или страниц; через `static_v`) |
| `landing_slider.js` | Лендинг |
| `playground.js`, `terminal_paste.js` | Плейграунд |
| `auth.js` | Login / signup / reset |

Правила paste в терминале должны совпадать на клиенте (`terminal_paste.js`) и сервере (`apps/core/terminal_paste.py`).

## Breakpoints

| Имя | Ширина | Файл |
| --- | --- | --- |
| Mobile | `< 768px` | `responsive.css` |
| Tablet | `768–1024px` | `responsive.css` |
| Desktop | `1024–1440px` | `responsive.css` |
| Wide | `> 1440px` | `responsive.css` |

Подробности коллапса сеток — в разделе Responsive Behavior в `DESIGN.md`.
