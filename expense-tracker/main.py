from fastmcp import FastMCP
import sqlite3
import os
import tempfile
import json

TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")


def init_db():
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("""
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    subcategory TEXT DEFAULT '',
                    note TEXT DEFAULT ''
                )
            """)
            c.execute(
                "INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')"
            )
            c.execute("DELETE FROM expenses WHERE category = 'test'")
            c.commit()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")
        raise

init_db()

@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    """Add a new expense entry."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                INSERT INTO expenses(date, amount, category, subcategory, note)
                VALUES (?,?,?,?,?)
                """,
                (date, amount, category, subcategory, note)
            )
            c.commit()
            return {
                "status": "success",
                "id": cur.lastrowid,
                "message": "Expense added successfully"
            }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}


@mcp.tool()
def list_expenses(start_date, end_date):
    """List expenses in a date range."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error listing expenses: {str(e)}"}


@mcp.tool()
def summarize(start_date, end_date, category=None):
    """Summarize expenses by category."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            query = """
                SELECT category, SUM(amount) AS total_amount, COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """
            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += " GROUP BY category ORDER BY total_amount DESC"

            cur = c.execute(query, params)
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        return {"status": "error", "message": f"Error summarizing expenses: {str(e)}"}


@mcp.tool()
def edit_expense(
    date,
    category,
    new_amount,
    new_date=None,
    new_subcategory=None,
    new_note=None
):
    """
    Edit an expense.
    If new_* is None, the existing value is preserved.
    """
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                UPDATE expenses
                SET
                    amount = ?,
                    date = COALESCE(?, date),
                    subcategory = COALESCE(?, subcategory),
                    note = COALESCE(?, note)
                WHERE date = ? AND category = ?
                """,
                (
                    new_amount,
                    new_date,
                    new_subcategory,
                    new_note,
                    date,
                    category
                )
            )
            c.commit()
            return {
                "status": "success",
                "updated_rows": cur.rowcount
            }
    except Exception as e:
        return {"status": "error", "message": f"Error editing expense: {str(e)}"}


@mcp.tool()
def delete_expense(date, category, note=""):
    """Delete expense(s) matching date, category, and note."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            cur = c.execute(
                """
                DELETE FROM expenses
                WHERE date = ? AND category = ? AND note = ?
                """,
                (date, category, note)
            )
            c.commit()
            return {
                "status": "success",
                "deleted_rows": cur.rowcount
            }
    except Exception as e:
        return {"status": "error", "message": f"Error deleting expense: {str(e)}"}


@mcp.resource("expense:///categories", mime_type="application/json")
def categories():
    try:
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }

        try:
            with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return json.dumps(default_categories, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Could not load categories: {str(e)}"})

# -------------------- Run --------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
