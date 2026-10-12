from validation_base_service import ValidationBaseService


class ValidatorService(ValidationBaseService):
    """Concrete implementation — schema is injected at instantiation."""

    def __init__(self, schema: dict):
        super().__init__(schema)
