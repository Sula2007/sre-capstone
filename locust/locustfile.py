from locust import HttpUser, task, between

class ShopUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def get_products(self):
        self.client.get("/products")

    @task(1)
    def health_check(self):
        self.client.get("/health")
