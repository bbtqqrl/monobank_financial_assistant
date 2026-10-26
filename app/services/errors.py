class ServiceError(Exception):
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidRequestError(ServiceError):
    status_code = 400


class NotFoundError(ServiceError):
    status_code = 404


class ConflictError(ServiceError):
    status_code = 409


class TooManyRequestsError(ServiceError):
    status_code = 429


class ServiceUnavailableError(ServiceError):
    status_code = 503
