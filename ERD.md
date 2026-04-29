Floriety Data Dictionary

users
- id INTEGER NO PK, AUTOINCREMENT — User primary key
- email TEXT NO UNIQUE — User email address
- password_hash TEXT NO — Hashed user password
- token TEXT YES — Auth token for session
- created_at TEXT YES datetime('now') — Record creation timestamp

profiles
- id INTEGER NO PK, AUTOINCREMENT — Profile primary key
- user_id INTEGER NO UNIQUE — FK to users(id)
- name TEXT YES '' — User display name
- nickname TEXT YES '' — User nickname
- description TEXT YES '' — Profile description
- avatar_index INTEGER YES 1 — Selected avatar index
- is_dark INTEGER YES 1 — Dark mode setting

scan_history
- id INTEGER NO PK, AUTOINCREMENT — Scan record primary key
- user_id INTEGER NO — FK to users(id)
- flower_name TEXT YES '' — Detected flower name
- scientific TEXT YES '' — Scientific name
- family TEXT YES '' — Plant family
- variety_appearance TEXT YES '' — Appearance details
- origin TEXT YES '' — Flower origin
- habitat TEXT YES '' — Natural habitat
- allergen TEXT YES '' — Allergen information
- disease TEXT YES '' — Disease notes
- care_list TEXT YES '' — Care instructions
- description TEXT YES '' — Description / notes
- image_url TEXT YES '' — Image or photo URL
- is_favorite INTEGER YES 0 — Favorite flag
- created_at TEXT YES datetime('now') — Scan timestamp

feedback
- id INTEGER NO PK, AUTOINCREMENT — Feedback primary key
- user_id INTEGER NO — FK to users(id)
- gmail TEXT YES '' — User email address
- subject TEXT YES '' — Feedback subject
- message TEXT YES '' — Feedback message
- created_at TEXT YES datetime('now') — Submission timestamp

chat_history
- id INTEGER NO PK, AUTOINCREMENT — Chat history primary key
- user_id INTEGER NO — FK to users(id)
- title TEXT YES 'Floriety Chat' — Chat session title
- messages TEXT YES '[]' — Stored messages JSON
- created_at TEXT YES datetime('now') — Creation timestamp
- updated_at TEXT YES
 datetime('now') — Last update timestamp
