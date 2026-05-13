terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = "npipe:////./pipe/docker_engine"
}

resource "docker_network" "sre_network" {
  name = "sre-network"
}

resource "docker_volume" "postgres_data" { name = "sre_postgres_data" }
resource "docker_volume" "grafana_data"  { name = "sre_grafana_data" }

resource "docker_container" "db" {
  name  = "sre-db"
  image = "postgres:15"
  networks_advanced { name = docker_network.sre_network.name }
  env = [
    "POSTGRES_DB=shopdb",
    "POSTGRES_USER=shopuser",
    "POSTGRES_PASSWORD=shoppass"
  ]
  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }
}

resource "docker_container" "backend" {
  name  = "sre-backend"
  image = "sre-backend:latest"
  networks_advanced { name = docker_network.sre_network.name }
  ports {
    internal = 8000
    external = 8001
  }
  env = [
    "DB_HOST=sre-db",
    "DB_NAME=shopdb",
    "DB_USER=shopuser",
    "DB_PASSWORD=shoppass"
  ]
  depends_on = [docker_container.db]
}

resource "docker_container" "prometheus" {
  name  = "sre-prometheus"
  image = "prom/prometheus:latest"
  networks_advanced { name = docker_network.sre_network.name }
  ports {
    internal = 9090
    external = 9090
  }
  volumes {
    host_path      = abspath("../app/prometheus/prometheus.yml")
    container_path = "/etc/prometheus/prometheus.yml"
  }
}

resource "docker_container" "grafana" {
  name  = "sre-grafana"
  image = "grafana/grafana:latest"
  networks_advanced { name = docker_network.sre_network.name }
  ports {
    internal = 3000
    external = 3001
  }
  env = [
    "GF_SECURITY_ADMIN_USER=admin",
    "GF_SECURITY_ADMIN_PASSWORD=admin123"
  ]
  volumes {
    volume_name    = docker_volume.grafana_data.name
    container_path = "/var/lib/grafana"
  }
}

resource "docker_container" "alertmanager" {
  name  = "sre-alertmanager"
  image = "prom/alertmanager:latest"
  networks_advanced { name = docker_network.sre_network.name }
  ports {
    internal = 9093
    external = 9093
  }
  volumes {
    host_path      = abspath("../app/alertmanager/alertmanager.yml")
    container_path = "/etc/alertmanager/alertmanager.yml"
  }
}
