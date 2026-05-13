from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
import os
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI(title="Shop Catalog API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['endpoint']
)
CHECKOUT_SUCCESS = Counter('checkout_success_total', 'Successful checkouts')
CHECKOUT_FAILURE = Counter('checkout_failure_total', 'Failed checkouts')

# DB connection
def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        database=os.getenv("DB_NAME", "shopdb"),
        user=os.getenv("DB_USER", "shopuser"),
        password=os.getenv("DB_PASSWORD", "shoppass")
    )

def init_db():
    for attempt in range(10):
        try:
            conn = get_db()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    price NUMERIC(10,2),
                    category VARCHAR(50),
                    stock INTEGER DEFAULT 0
                )
            """)
            cur.execute("SELECT COUNT(*) FROM products")
            count = cur.fetchone()[0]
            if count == 0:
                cur.executemany(
                    "INSERT INTO products (name, description, price, category, stock) VALUES (%s, %s, %s, %s, %s)",
                    [
                        ("iPhone 15", "Apple smartphone 128GB", 599.99, "Electronics", 50),
                        ("Samsung TV 55\"", "4K Smart TV", 799.99, "Electronics", 20),
                        ("Nike Air Max", "Running shoes size 42", 129.99, "Clothing", 100),
                        ("Coffee Maker", "Automatic espresso machine", 249.99, "Home", 30),
                        ("Python Book", "Learn Python in 30 days", 39.99, "Books", 200),
                        ("Headphones Sony", "Wireless noise-cancelling", 199.99, "Electronics", 45),
                        ("Yoga Mat", "Non-slip 6mm thick", 29.99, "Sports", 80),
                        ("Desk Lamp LED", "Adjustable brightness", 49.99, "Home", 60),
                    ]
                )
            conn.commit()
            cur.close()
            conn.close()
            print("DB initialized successfully")
            return
        except Exception as e:
            print(f"DB not ready (attempt {attempt+1}): {e}")
            time.sleep(3)

@app.on_event("startup")
def startup():
    init_db()

class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float
    category: Optional[str] = None
    stock: int = 0

class CheckoutRequest(BaseModel):
    product_id: int
    quantity: int

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/health")
def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health", status="200").inc()
    return {"status": "ok"}

@app.get("/products", response_model=List[Product])
def get_products(category: Optional[str] = None):
    start = time.time()
    try:
        conn = get_db()
        cur = conn.cursor()
        if category:
            cur.execute("SELECT id, name, description, price, category, stock FROM products WHERE category=%s", (category,))
        else:
            cur.execute("SELECT id, name, description, price, category, stock FROM products")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        products = [Product(id=r[0], name=r[1], description=r[2], price=r[3], category=r[4], stock=r[5]) for r in rows]
        REQUEST_COUNT.labels(method="GET", endpoint="/products", status="200").inc()
        return products
    except Exception as e:
        REQUEST_COUNT.labels(method="GET", endpoint="/products", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.labels(endpoint="/products").observe(time.time() - start)

@app.get("/products/{product_id}", response_model=Product)
def get_product(product_id: int):
    start = time.time()
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, name, description, price, category, stock FROM products WHERE id=%s", (product_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            REQUEST_COUNT.labels(method="GET", endpoint="/products/id", status="404").inc()
            raise HTTPException(status_code=404, detail="Product not found")
        REQUEST_COUNT.labels(method="GET", endpoint="/products/id", status="200").inc()
        return Product(id=row[0], name=row[1], description=row[2], price=row[3], category=row[4], stock=row[5])
    finally:
        REQUEST_LATENCY.labels(endpoint="/products/id").observe(time.time() - start)

@app.post("/checkout")
def checkout(req: CheckoutRequest):
    start = time.time()
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT stock FROM products WHERE id=%s", (req.product_id,))
        row = cur.fetchone()
        if not row:
            CHECKOUT_FAILURE.inc()
            raise HTTPException(status_code=404, detail="Product not found")
        if row[0] < req.quantity:
            CHECKOUT_FAILURE.inc()
            REQUEST_COUNT.labels(method="POST", endpoint="/checkout", status="400").inc()
            raise HTTPException(status_code=400, detail="Not enough stock")
        cur.execute("UPDATE products SET stock = stock - %s WHERE id=%s", (req.quantity, req.product_id))
        conn.commit()
        cur.close()
        conn.close()
        CHECKOUT_SUCCESS.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/checkout", status="200").inc()
        return {"status": "success", "message": f"Order placed for {req.quantity} item(s)"}
    except HTTPException:
        raise
    except Exception as e:
        CHECKOUT_FAILURE.inc()
        REQUEST_COUNT.labels(method="POST", endpoint="/checkout", status="500").inc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        REQUEST_LATENCY.labels(endpoint="/checkout").observe(time.time() - start)
