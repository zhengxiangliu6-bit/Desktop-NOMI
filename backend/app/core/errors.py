class AppError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(code)


class ProviderRequestError(AppError):
    def __init__(self):
        super().__init__(
            502, "UPSTREAM_ERROR", "模型服务请求失败，请检查后端配置或稍后重试。", True
        )


class ProviderTimeoutError(AppError):
    def __init__(self):
        super().__init__(504, "UPSTREAM_TIMEOUT", "模型服务响应超时，请稍后重试。", True)


class ModelFormatError(AppError):
    def __init__(self):
        super().__init__(
            502, "UPSTREAM_INVALID_RESPONSE", "模型回复格式无效，未加入对话上下文。", True
        )


def missing_configuration() -> AppError:
    return AppError(503, "CONFIGURATION_MISSING", "OpenAI Provider 配置不完整。")
