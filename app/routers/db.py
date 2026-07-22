from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from core.config import get_db_credentials

router = APIRouter()

def get_db_connection():
    creds = get_db_credentials()
    try:
        conn = psycopg2.connect(
            host=creds["host"],
            port=creds["port"],
            dbname=creds["dbname"],
            user=creds["username"],
            password=creds["password"]
        )
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

class ItemCreate(BaseModel):
    name: str
    description: str = None

@router.post("/init", summary="Initialize the database table")
def init_db():
    """Create the items table if it does not exist."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT
                )
            """)
        conn.commit()
        return {"status": "Database initialized successfully"}
    finally:
        conn.close()

@router.post("/items", summary="Create a new item")
def create_item(item: ItemCreate):
    """Insert a new item into the database."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO items (name, description) VALUES (%s, %s) RETURNING id, name, description",
                (item.name, item.description)
            )
            new_item = cur.fetchone()
        conn.commit()
        return new_item
    finally:
        conn.close()

@router.get("/items", summary="List all items")
def list_items():
    """Retrieve all items from the database."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, name, description FROM items ORDER BY id ASC")
            items = cur.fetchall()
        return items
    finally:
        conn.close()

@router.delete("/items/{item_id}", summary="Delete an item by ID")
def delete_item(item_id: int):
    """Delete a specific item from the database."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM items WHERE id = %s RETURNING id", (item_id,))
            deleted = cur.fetchone()
            if not deleted:
                raise HTTPException(status_code=404, detail="Item not found")
        conn.commit()
        return {"status": "Item deleted", "id": item_id}
    finally:
        conn.close()
