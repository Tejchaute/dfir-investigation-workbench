class ApplicationError(Exception):
    """Base error safe to translate at the API boundary."""

    status_code = 500
    code = "application_error"


class ValidationError(ApplicationError):
    status_code = 422
    code = "validation_error"


class NotFoundError(ApplicationError):
    status_code = 404
    code = "not_found"


class ProcessingError(ApplicationError):
    code = "processing_error"


class ForensicParsingError(ProcessingError):
    code = "forensic_parsing_error"


class InfrastructureError(ApplicationError):
    code = "infrastructure_error"
