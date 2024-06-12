from locust import HttpUser, task, constant
import random

class TelemetryAPI(HttpUser):
    wait_time = constant(1)

    @task
    def get_users(self):
        for _ in range(random.randint(1, 100)):
            self.client.get("/")

    @task
    def external(self):
        for _ in range(random.randint(1, 100)):
            self.client.get("/fetch-data")

            

   
