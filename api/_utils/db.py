import os
import psycopg2
import psycopg2.extras


def get_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')


def query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    conn = get_connection()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        if commit:
            conn.commit()
            if cur.description:
                return dict(cur.fetchone()) if fetchone else [dict(r) for r in cur.fetchall()]
            return cur.rowcount
        if fetchone:
            row = cur.fetchone()
            return dict(row) if row else None
        if fetchall:
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()
