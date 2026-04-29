"""
Floriety Backend — Flask REST API + SQLite
Run: python server.py
"""

import os
import sqlite3
import hashlib
import uuid
import json
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'floriety.db')

# ─── Database helpers ────────────────────────────────────────────────

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            token TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            nickname TEXT DEFAULT '',
            description TEXT DEFAULT '',
            avatar_index INTEGER DEFAULT 1,
            is_dark INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            flower_name TEXT DEFAULT '',
            scientific TEXT DEFAULT '',
            family TEXT DEFAULT '',
            variety_appearance TEXT DEFAULT '',
            origin TEXT DEFAULT '',
            habitat TEXT DEFAULT '',
            allergen TEXT DEFAULT '',
            disease TEXT DEFAULT '',
            care_list TEXT DEFAULT '',
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            is_favorite INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            gmail TEXT DEFAULT '',
            subject TEXT DEFAULT '',
            message TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT DEFAULT 'Floriety Chat',
            messages TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    ''')

    # Migrate existing profile table if needed.
    try:
        existing_columns = [row[1] for row in db.execute("PRAGMA table_info(profiles)").fetchall()]
        if 'avatar_index' not in existing_columns:
            db.execute('ALTER TABLE profiles ADD COLUMN avatar_index INTEGER DEFAULT 1')
        if 'is_dark' not in existing_columns:
            db.execute('ALTER TABLE profiles ADD COLUMN is_dark INTEGER DEFAULT 1')
    except Exception:
        pass

    db.commit()

    # Seed base user accounts if the system is empty.
    cursor = db.execute('SELECT COUNT(*) as c FROM users')
    total_users = cursor.fetchone()[0]
    if total_users == 0:
        seed_users = [
            {'email': 'amelia@floriety.ai', 'password': 'password123'},
            {'email': 'noah@floriety.ai', 'password': 'password123'},
            {'email': 'maya@floriety.ai', 'password': 'password123'},
        ]
        for user in seed_users:
            password_hash = hashlib.sha256(user['password'].encode()).hexdigest()
            db.execute(
                'INSERT INTO users (email, password_hash, token) VALUES (?, ?, ?)',
                (user['email'], password_hash, None)
            )
            user_id = db.execute('SELECT id FROM users WHERE email = ?', (user['email'],)).fetchone()['id']
            name = user['email'].split('@')[0].title()
            db.execute(
                'INSERT INTO profiles (user_id, name, nickname, description, avatar_index, is_dark) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, name, '', '', 1, 1)
            )
        db.commit()
    db.close()


# ─── Auth helpers ────────────────────────────────────────────────────

def _hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def _generate_token():
    return uuid.uuid4().hex


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE token = ?', (token,)).fetchone()
        if not user:
            return jsonify({'error': 'Invalid token'}), 401
        g.user = dict(user)
        return f(*args, **kwargs)
    return decorated


# ─── Auth endpoints ──────────────────────────────────────────────────

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    if len(password) < 4:
        return jsonify({'error': 'Password must be at least 4 characters'}), 400

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    pw_hash = _hash_password(password)
    token = _generate_token()
    cursor = db.execute(
        'INSERT INTO users (email, password_hash, token) VALUES (?, ?, ?)',
        (email, pw_hash, token)
    )
    user_id = cursor.lastrowid

    # Create empty profile with email as name and default appearance settings
    name = email.split('@')[0].title()
    db.execute(
        'INSERT INTO profiles (user_id, name, nickname, description, avatar_index, is_dark) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, name, '', '', 1, 1)
    )
    db.commit()

    return jsonify({
        'token': token,
        'user_id': user_id,
        'email': email,
        'name': name,
    }), 201


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not user or user['password_hash'] != _hash_password(password):
        return jsonify({'error': 'Invalid email or password'}), 401

    token = _generate_token()
    db.execute('UPDATE users SET token = ? WHERE id = ?', (token, user['id']))
    db.commit()

    profile = db.execute('SELECT * FROM profiles WHERE user_id = ?', (user['id'],)).fetchone()
    result = {
        'token': token,
        'user_id': user['id'],
        'email': user['email'],
    }
    if profile:
        result.update({
            'name': profile['name'],
            'nickname': profile['nickname'],
            'description': profile['description'],
            'avatar_index': profile['avatar_index'],
            'is_dark': bool(profile['is_dark']),
        })
    else:
        result.update({
            'name': email.split('@')[0].title(),
            'nickname': '',
            'description': '',
            'avatar_index': 1,
            'is_dark': True,
        })

    return jsonify(result), 200


# ─── Profile endpoints ──────────────────────────────────────────────

@app.route('/api/profile', methods=['GET'])
@require_auth
def get_profile():
    db = get_db()
    profile = db.execute(
        'SELECT * FROM profiles WHERE user_id = ?', (g.user['id'],)
    ).fetchone()
    if not profile:
        return jsonify({
            'name': '',
            'nickname': '',
            'description': '',
            'avatar_index': 1,
            'is_dark': True,
        }), 200
    return jsonify({
        'name': profile['name'],
        'nickname': profile['nickname'],
        'description': profile['description'],
        'avatar_index': profile['avatar_index'],
        'is_dark': bool(profile['is_dark']),
    }), 200


@app.route('/api/profile', methods=['PUT'])
@require_auth
def update_profile():
    data = request.get_json() or {}
    name = data.get('name', '').strip()
    nickname = data.get('nickname', '').strip()
    description = data.get('description', '').strip()
    avatar_index = int(data.get('avatar_index', 1)) if data.get('avatar_index') is not None else 1
    is_dark = 1 if data.get('is_dark', True) else 0

    if avatar_index < 1:
        avatar_index = 1

    db = get_db()
    existing = db.execute(
        'SELECT id FROM profiles WHERE user_id = ?', (g.user['id'],)
    ).fetchone()

    if existing:
        db.execute(
            'UPDATE profiles SET name = ?, nickname = ?, description = ?, avatar_index = ?, is_dark = ? WHERE user_id = ?',
            (name, nickname, description, avatar_index, is_dark, g.user['id'])
        )
    else:
        db.execute(
            'INSERT INTO profiles (user_id, name, nickname, description, avatar_index, is_dark) VALUES (?, ?, ?, ?, ?, ?)',
            (g.user['id'], name or g.user['email'].split('@')[0].title(), nickname, description, avatar_index, is_dark)
        )
    db.commit()
    return jsonify({'message': 'Profile updated'}), 200


# ─── History endpoints ───────────────────────────────────────────────

@app.route('/api/history', methods=['GET'])
@require_auth
def get_history():
    db = get_db()
    rows = db.execute(
        'SELECT * FROM scan_history WHERE user_id = ? ORDER BY created_at DESC',
        (g.user['id'],)
    ).fetchall()
    items = []
    for r in rows:
        items.append({
            'id': r['id'],
            'flower_name': r['flower_name'],
            'scientific': r['scientific'],
            'family': r['family'],
            'variety_appearance': r['variety_appearance'],
            'origin': r['origin'],
            'habitat': r['habitat'],
            'allergen': r['allergen'],
            'disease': r['disease'],
            'care_list': r['care_list'],
            'description': r['description'],
            'image_url': r['image_url'],
            'is_favorite': bool(r['is_favorite']),
            'created_at': r['created_at'],
        })
    return jsonify(items), 200


@app.route('/api/history', methods=['POST'])
@require_auth
def add_history():
    data = request.get_json() or {}
    db = get_db()

    flower_name = data.get('flower_name', data.get('name', ''))
    image_query = flower_name.replace(' ', '+') if flower_name else 'flower'
    image_url = data.get('image_url', f'https://source.unsplash.com/600x400/?{image_query},flower')

    db.execute(
        '''INSERT INTO scan_history
           (user_id, flower_name, scientific, family, variety_appearance,
            origin, habitat, allergen, disease, care_list, description, image_url)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (
            g.user['id'],
            flower_name,
            data.get('scientific', ''),
            data.get('family', ''),
            data.get('variety_appearance', ''),
            data.get('origin', ''),
            data.get('habitat', ''),
            data.get('allergen', ''),
            data.get('disease', ''),
            data.get('care_list', ''),
            data.get('description', ''),
            image_url,
        )
    )
    db.commit()
    return jsonify({'message': 'History saved'}), 201


@app.route('/api/history/<int:history_id>/favorite', methods=['PUT'])
@require_auth
def toggle_favorite(history_id):
    db = get_db()
    item = db.execute(
        'SELECT * FROM scan_history WHERE id = ? AND user_id = ?',
        (history_id, g.user['id'])
    ).fetchone()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    new_val = 0 if item['is_favorite'] else 1
    db.execute(
        'UPDATE scan_history SET is_favorite = ? WHERE id = ?',
        (new_val, history_id)
    )
    db.commit()
    return jsonify({'is_favorite': bool(new_val)}), 200


@app.route('/api/history/<int:history_id>', methods=['DELETE'])
@require_auth
def delete_history(history_id):
    db = get_db()
    item = db.execute(
        'SELECT id FROM scan_history WHERE id = ? AND user_id = ?',
        (history_id, g.user['id'])
    ).fetchone()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    db.execute('DELETE FROM scan_history WHERE id = ?', (history_id,))
    db.commit()
    return jsonify({'message': 'Deleted'}), 200


# ─── Feedback endpoints ─────────────────────────────────────────────

@app.route('/api/feedback', methods=['POST'])
@require_auth
def submit_feedback():
    data = request.get_json() or {}
    gmail = (data.get('gmail') or '').strip()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()

    if not subject or not message:
        return jsonify({'error': 'Subject and message are required'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO feedback (user_id, gmail, subject, message) VALUES (?, ?, ?, ?)',
        (g.user['id'], gmail, subject, message)
    )
    db.commit()
    return jsonify({'message': 'Feedback submitted'}), 201


@app.route('/api/feedback', methods=['GET'])
def get_all_feedback():
    """Admin endpoint — no auth required for owner dashboard."""
    db = get_db()
    rows = db.execute('''
        SELECT f.*, u.email as user_email
        FROM feedback f
        JOIN users u ON f.user_id = u.id
        ORDER BY f.created_at DESC
    ''').fetchall()
    items = []
    for r in rows:
        items.append({
            'id': r['id'],
            'user_email': r['user_email'],
            'gmail': r['gmail'],
            'subject': r['subject'],
            'message': r['message'],
            'created_at': r['created_at'],
        })
    return jsonify(items), 200


# ─── Chatbot history endpoints ───────────────────────────────────────

@app.route('/api/chat/history', methods=['GET'])
@require_auth
def get_chat_history():
    db = get_db()
    rows = db.execute(
        'SELECT id, title, created_at, updated_at FROM chat_history WHERE user_id = ? ORDER BY updated_at DESC',
        (g.user['id'],)
    ).fetchall()
    result = []
    for r in rows:
        result.append({
            'id': r['id'],
            'title': r['title'],
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        })
    return jsonify(result), 200


@app.route('/api/chat/history/<int:history_id>', methods=['GET'])
@require_auth
def get_chat_history_item(history_id):
    db = get_db()
    row = db.execute(
        'SELECT * FROM chat_history WHERE id = ? AND user_id = ?',
        (history_id, g.user['id'])
    ).fetchone()
    if not row:
        return jsonify({'error': 'Chat history not found'}), 404
    return jsonify({
        'id': row['id'],
        'title': row['title'],
        'messages': json.loads(row['messages'] or '[]'),
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }), 200


@app.route('/api/chat/history', methods=['POST'])
@require_auth
def save_chat_history():
    data = request.get_json() or {}
    title = (data.get('title') or 'Floriety Chat').strip()
    messages = data.get('messages', [])
    if not isinstance(messages, list) or len(messages) == 0:
        return jsonify({'error': 'Messages are required'}), 400

    if not title:
        first_user = next((m for m in messages if m.get('role') == 'user'), None)
        title = first_user.get('content', 'Floriety Chat')[:48] if first_user else 'Floriety Chat'

    messages_json = json.dumps(messages)
    db = get_db()
    existing_id = data.get('id')

    if existing_id is not None:
        existing = db.execute(
            'SELECT id FROM chat_history WHERE id = ? AND user_id = ?',
            (existing_id, g.user['id'])
        ).fetchone()
        if existing:
            db.execute(
                'UPDATE chat_history SET title = ?, messages = ?, updated_at = datetime("now") WHERE id = ? AND user_id = ?',
                (title, messages_json, existing_id, g.user['id'])
            )
        else:
            return jsonify({'error': 'Chat history not found'}), 404
    else:
        cursor = db.execute(
            'INSERT INTO chat_history (user_id, title, messages) VALUES (?, ?, ?)',
            (g.user['id'], title, messages_json)
        )
        existing_id = cursor.lastrowid

    # Keep only latest 5 chat sessions.
    rows = db.execute(
        'SELECT id FROM chat_history WHERE user_id = ? ORDER BY updated_at DESC',
        (g.user['id'],)
    ).fetchall()
    ids = [r['id'] for r in rows]
    if len(ids) > 5:
        remove_ids = ids[5:]
        db.execute(
            'DELETE FROM chat_history WHERE id IN ({})'.format(','.join('?' for _ in remove_ids)),
            remove_ids
        )

    db.commit()
    return jsonify({'id': existing_id, 'message': 'Chat history saved'}), 200


# ─── Admin endpoints ────────────────────────────────────────────────

@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    db = get_db()
    rows = db.execute('''
        SELECT id, email, created_at
        FROM users
        ORDER BY created_at DESC
    ''').fetchall()
    users = []
    for r in rows:
        users.append({
            'id': r['id'],
            'email': r['email'],
            'created_at': r['created_at'],
        })
    return jsonify(users), 200


@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def admin_update_user(user_id):
    data = request.get_json() or {}
    db = get_db()

    user = db.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if 'email' in data:
        db.execute('UPDATE users SET email = ? WHERE id = ?', (data['email'].strip().lower(), user_id))

    if 'password' in data and data['password']:
        if len(data['password']) < 4:
            return jsonify({'error': 'Password must be at least 4 characters'}), 400
        db.execute(
            'UPDATE users SET password_hash = ? WHERE id = ?',
            (_hash_password(data['password']), user_id)
        )

    db.commit()
    return jsonify({'message': 'User updated'}), 200


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def admin_delete_user(user_id):
    db = get_db()
    user = db.execute('SELECT id FROM users WHERE id = ?', (user_id,)).fetchone()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    db.execute('DELETE FROM users WHERE id = ?', (user_id,))
    db.commit()
    return jsonify({'message': 'User deleted'}), 200


@app.route('/api/admin/analytics', methods=['GET'])
def admin_analytics():
    db = get_db()

    total_users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    total_scans = db.execute('SELECT COUNT(*) as c FROM scan_history').fetchone()['c']
    total_feedbacks = db.execute('SELECT COUNT(*) as c FROM feedback').fetchone()['c']
    total_favorites = db.execute('SELECT COUNT(*) as c FROM scan_history WHERE is_favorite = 1').fetchone()['c']

    # Monthly user registrations (last 12 months)
    monthly_users = db.execute('''
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM users
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''').fetchall()

    # Monthly scans
    monthly_scans = db.execute('''
        SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count
        FROM scan_history
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
    ''').fetchall()

    # Top scanned flowers
    top_flowers = db.execute('''
        SELECT flower_name, COUNT(*) as count
        FROM scan_history
        WHERE flower_name != ''
        GROUP BY flower_name
        ORDER BY count DESC
        LIMIT 10
    ''').fetchall()

    return jsonify({
        'total_users': total_users,
        'total_scans': total_scans,
        'total_feedbacks': total_feedbacks,
        'total_favorites': total_favorites,
        'monthly_users': [{'month': r['month'], 'count': r['count']} for r in monthly_users],
        'monthly_scans': [{'month': r['month'], 'count': r['count']} for r in monthly_scans],
        'top_flowers': [{'name': r['flower_name'], 'count': r['count']} for r in top_flowers],
    }), 200


# ─── Main ────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    print("✿ Floriety API running on http://0.0.0.0:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
