# checkin-system

system för RVL RASA

\# Check-In System



A full-stack workforce check-in platform built solo, end to end, and deployed in

production for a real service business. Field staff check in and out of jobs from a

mobile app; managers schedule work, message staff, and review activity from a web

admin panel — all served by a Python REST API over a managed PostgreSQL database.



\*\*Stack at a glance:\*\* Python · Flask · SQLAlchemy · PostgreSQL · React Native (Expo) · PWA · Render



\---



\## Overview



This system replaces manual, paper-based job tracking for a field-service company.

It has three parts that share one backend:



\- \*\*Backend\*\* — a modular Flask REST API (separate API and web-route modules) with

&#x20; SQLAlchemy models and database migrations, backed by PostgreSQL.

\- \*\*Web admin panel\*\* — an installable PWA for managers (scheduling, history,

&#x20; messaging, oversight).

\- \*\*Mobile app\*\* — a React Native / Expo application with a native Android build,

&#x20; used by field staff to check in and out on site.



It was deployed on Render against a Supabase-managed PostgreSQL instance and used

daily in a live business.



> This is a real production system, not a tutorial project. It has been de-identified

> for this public repository — original branding and customer/staff data have been removed.



\---



\## Architecture



```

&#x20; Field staff (on site)              Managers (browser)

&#x20; +---------------------+           +---------------------+

&#x20; |  Mobile app         |           |  Web admin (PWA)    |

&#x20; |  React Native/Expo  |           |  installable        |

&#x20; +----------+----------+           +----------+----------+

&#x20;            |                                  |

&#x20;            +---------------+------------------+

&#x20;                            | HTTPS / REST

&#x20;                   +--------v---------+

&#x20;                   |  Flask REST API  |     deployed on Render

&#x20;                   |  (Python)        |

&#x20;                   |  SQLAlchemy +    |

&#x20;                   |  migrations      |

&#x20;                   +--------+---------+

&#x20;                            |

&#x20;                   +--------v---------+

&#x20;                   |  PostgreSQL      |     managed by Supabase

&#x20;                   +------------------+

```



The backend is organized as a set of focused modules rather than one monolith:



| Area        | Responsibility                              |

|-------------|---------------------------------------------|

| Auth        | Login, sessions, user management            |

| Check-in    | Job check-in / check-out for field staff    |

| Scheduling  | Assigning and planning jobs                 |

| Messaging   | In-app messaging between staff and managers |

| History     | Activity history and reporting              |

| Admin       | Management / oversight panel                |



\---



\## Features



\- \*\*Authentication \& user management\*\* — staff and manager accounts.

\- \*\*Job check-in / check-out\*\* — field staff log start and end of jobs from the mobile app.

\- \*\*Scheduling\*\* — managers plan and assign work.

\- \*\*In-app messaging\*\* — direct communication between staff and managers.

\- \*\*Activity history \& reporting\*\* — review and export past activity.

\- \*\*Admin panel\*\* — central oversight for managers.



\---



\## Tech stack



\*\*Backend\*\*

\- Python, Flask (modular structure: separate API and web-route modules)

\- SQLAlchemy ORM with database migrations

\- PostgreSQL (Supabase-managed)



\*\*Web admin\*\*

\- Progressive Web App (web manifest + service worker), installable on desktop and mobile



\*\*Mobile\*\*

\- React Native with Expo

\- Native Android build



\*\*Infrastructure\*\*

\- Render (API hosting)

\- Supabase (managed PostgreSQL)



\---



\## Project structure



```

checkin-system/

├── backend/                 # Flask REST API

│   ├── api\_\*.py             # API modules (auth, check-in, schedule, chat, user, …)

│   ├── routes\*.py           # Web admin routes

│   ├── models.py            # SQLAlchemy models

│   ├── migrations/          # Database migrations

│   ├── config.py            # Configuration

│   ├── app.py               # Application entry point

│   └── requirements.txt

│

└── frontend/

&#x20;   ├── admin.html           # PWA admin panel

&#x20;   ├── manifest.json        # Web app manifest

&#x20;   ├── service-worker.js    # Offline / install support

&#x20;   └── checkin-app/         # React Native / Expo mobile app

&#x20;       └── android/         # Native Android project

```



\---



\## Running locally



\### Backend



```bash

cd backend

python -m venv venv

\# Windows:

venv\\Scripts\\activate

\# macOS / Linux:

\# source venv/bin/activate



pip install -r requirements.txt



\# Configure environment

cp .env.example .env        # then set DATABASE\_URL



\# Apply database migrations

flask db upgrade



\# Run

python app.py

```



\### Mobile app



```bash

cd frontend/checkin-app

npm install

npx expo start

```



> Exact commands may vary with your local setup; adjust the entry point and migration

> commands to match your environment.



\---



\## Notes



\- \*\*De-identified:\*\* original company branding, logos, and real customer/staff data

&#x20; have been removed for this public repository.

\- \*\*Secrets:\*\* no credentials are committed. Copy `.env.example` to `.env` and supply

&#x20; your own values.

