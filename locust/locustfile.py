from locust import HttpUser, task, between
import random


class ShopUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # fetch available product IDs once per simulated user
        resp = self.client.get("/products", name="/products (setup)")
        if resp.status_code == 200:
            products = resp.json()
            self.product_ids = [p["id"] for p in products if p.get("stock", 0) > 0]
        else:
            self.product_ids = [1, 2, 3]

    @task(3)
    def browse_products(self):
        self.client.get("/products")

    @task(2)
    def view_product(self):
        if self.product_ids:
            pid = random.choice(self.product_ids)
            self.client.get(f"/products/{pid}", name="/products/[id]")

    @task(1)
    def checkout(self):
        if self.product_ids:
            pid = random.choice(self.product_ids)
            self.client.post(
                "/checkout",
                json={"product_id": pid, "quantity": 1},
                name="/checkout",
            )

    @task(1)
    def health_check(self):
        self.client.get("/health")
