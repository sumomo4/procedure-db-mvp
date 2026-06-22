"""FastAPI entry point for the standard API."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.responses import error_response
from app.routers import case_docs, health, modules, source_docs, statuses


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application.
    """

    settings = get_settings()
    application = FastAPI(
        title="Procedure DB standard API",
        version="0.1.0",
        description="Sprint 1 FastAPI foundation for the standard MVP.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allow_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(health.router, prefix=settings.api_prefix)
    application.include_router(modules.router, prefix=settings.api_prefix)
    application.include_router(source_docs.router, prefix=settings.api_prefix)
    application.include_router(statuses.router, prefix=settings.api_prefix)
    application.include_router(case_docs.router, prefix=settings.api_prefix)

    @application.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exception: HTTPException,
    ) -> JSONResponse:
        """Return the common error envelope for HTTP exceptions.

        Args:
            request: Incoming request.
            exception: HTTP exception raised by route handlers.

        Returns:
            JSON response with the common error envelope.
        """

        del request
        return JSONResponse(
            status_code=exception.status_code,
            content=error_response(str(exception.detail)).model_dump(),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exception: RequestValidationError,
    ) -> JSONResponse:
        """Return the common error envelope for request validation errors.

        Args:
            request: Incoming request.
            exception: Validation exception raised by FastAPI.

        Returns:
            JSON response with the common error envelope.
        """

        del request
        error_count = len(exception.errors())
        return JSONResponse(
            status_code=400,
            content=error_response(f"Request validation failed: {error_count} error(s).").model_dump(),
        )

    return application


app = create_app()
