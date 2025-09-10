from flask import Flask, render_template, request, redirect, session
import sqlite3
import time
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'  # Change this in production!

def init_db():
    conn = sqlite3.connect("lfg.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT,
                    platform TEXT,
                    relic TEXT,
                    description TEXT,
                    ign TEXT,
                    timestamp INTEGER,
                    user_session TEXT
                )''')
    
    # Add user_session column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE posts ADD COLUMN user_session TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # Column already exists
    
    conn.close()

init_db()

@app.route("/")
def index():
    # Create a session ID if one doesn't exist
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    category_filter = request.args.get("category", "All")
    platform_filter = request.args.get("platform", "All")
    relic_filter = request.args.get("relic", "").strip()
    show_mine = request.args.get("show_mine", "false") == "true"

    conn = sqlite3.connect("lfg.db")
    c = conn.cursor()

    cutoff = int(time.time()) - 60*60*4  # expire after 4h
    c.execute("DELETE FROM posts WHERE timestamp < ?", (cutoff,))
    conn.commit()

    query = "SELECT * FROM posts WHERE 1=1"
    params = []

    if show_mine:
        query += " AND user_session=?"
        params.append(session['user_id'])
    else:
        if category_filter != "All":
            query += " AND category=?"
            params.append(category_filter)

        if platform_filter != "All":
            query += " AND platform=?"
            params.append(platform_filter)

        if relic_filter:
            query += " AND relic LIKE ?"
            params.append(f"%{relic_filter.upper()}%")

    query += " ORDER BY timestamp DESC"
    c.execute(query, params)
    posts = c.fetchall()
    conn.close()

    categories = ["All", "Relics", "Archimedea", "Netracells", "Eidolons", "Steel Path", "Endo", "General Help"]

    return render_template("index.html",
                           posts=posts,
                           categories=categories,
                           category_filter=category_filter,
                           platform_filter=platform_filter,
                           relic_filter=relic_filter,
                           show_mine=show_mine,
                           user_session=session['user_id'])

@app.route("/add", methods=["POST"])
def add_post():
    # Create a session ID if one doesn't exist
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    
    category = request.form["category"]
    platform = request.form["platform"]
    ign = request.form["ign"]
    
    # Handle relic and description based on category
    if category == "Relics":
        relic = request.form.get("relic", "").strip().upper()
        description = f"Running {relic}" if relic else "Running relic"
    else:
        relic = ""  # No relic for non-relic categories
        description = request.form.get("description", "").strip()
    
    # Validate required fields
    if not ign.strip():
        return redirect("/")  # Could add flash message here
    
    if category == "Relics" and not relic:
        return redirect("/")  # Could add flash message here
    
    if category != "Relics" and not description:
        return redirect("/")  # Could add flash message here

    conn = sqlite3.connect("lfg.db")
    c = conn.cursor()
    c.execute("INSERT INTO posts (category, platform, relic, description, ign, timestamp, user_session) VALUES (?, ?, ?, ?, ?, ?, ?)",
              (category, platform, relic, description, ign, int(time.time()), session['user_id']))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/delete/<int:post_id>", methods=["POST"])
def delete_post(post_id):
    if 'user_id' not in session:
        return redirect("/")
    
    conn = sqlite3.connect("lfg.db")
    c = conn.cursor()
    # Only allow deletion if the post belongs to the current user
    c.execute("DELETE FROM posts WHERE id=? AND user_session=?", (post_id, session['user_id']))
    conn.commit()
    conn.close()
    
    # Redirect back to where they came from
    if request.args.get("show_mine") == "true":
        return redirect("/?show_mine=true")
    return redirect("/")
    
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)