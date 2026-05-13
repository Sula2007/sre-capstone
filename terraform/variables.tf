variable "db_name" {
  default = "shopdb"
}
variable "db_user" {
  default = "shopuser"
}
variable "db_password" {
  default   = "shoppass"
  sensitive = true
}
variable "backend_port" {
  default = 8000
}
