import logging
from ..configs.infrastructure_config import InfrastructureConfig
from ..configs.market_config import MarketConfig
from ..configs.security_config import SecurityConfig

class InfrastructureValidator:
    @staticmethod
    def validate_infrastructure(config: InfrastructureConfig) -> bool:
        try:
            # Validate environments
            required_envs = ["development", "production"]
            if not all(env in config.environments for env in required_envs):
                return False
                
            # Validate deployment
            valid_strategies = ["rolling", "blue-green", "canary"]
            if config.deployment["strategy"] not in valid_strategies:
                return False
                
            # Validate monitoring
            if config.monitoring["metrics"]["collection"]["providers"] and \
               not config.monitoring["metrics"]["storage"]["provider"]:
                return False
                
            return True
        except Exception as e:
            logging.error(f"Infrastructure validation error: {e}")
            return False

class SecurityValidator:
    @staticmethod
    def validate_security(config: SecurityConfig) -> bool:
        try:
            # Validate authentication
            if not config.authentication["providers"]:
                return False
                
            # Validate authorization
            required_roles = ["admin", "viewer"]
            if not all(role in config.authorization["roles"] for role in required_roles):
                return False
                
            return True
        except Exception as e:
            logging.error(f"Security validation error: {e}")
            return False 