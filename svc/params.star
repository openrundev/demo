param("service", description="Service to operate on", default="api")
param("options_service", type=LIST, default=["api", "worker", "scheduler"])

param("env", description="Environment", default="staging")
param("options_env", type=LIST, default=["staging", "prod"])

param("replicas", type=INT, description="Instances to restart, one at a time", default=2)
