"""
Error Handlers

This module provides centralized error handling for the Flask application.
"""

from flask import jsonify, render_template, request

from utils.logger import logger


def handle_400(error):
    """Handle 400 Bad Request errors."""
    logger.warning(f"400 error: {error} - URL: {request.url}")

    if request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Bad request",
                    "message": "The request could not be understood by the server",
                }
            ),
            400,
        )

    context = {
        "error_code": 400,
        "error_message": "Bad Request",
        "error_description": "The request could not be understood by the server",
        "allowed_types": [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
    }

    return render_template("error.html", **context), 400


def handle_403(error):
    """Handle 403 Forbidden errors."""
    logger.warning(f"403 error: {error} - URL: {request.url}")

    if request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Forbidden",
                    "message": "You do not have permission to access this resource",
                }
            ),
            403,
        )

    context = {
        "error_code": 403,
        "error_message": "Forbidden",
        "error_description": "You do not have permission to access this resource",
        "allowed_types": [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
    }

    return render_template("error.html", **context), 403


def handle_404(error):
    """Handle 404 Not Found errors."""
    logger.info(f"404 error: {error} - URL: {request.url}")

    if request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Not found",
                    "message": "The requested resource was not found",
                }
            ),
            404,
        )

    context = {
        "error_code": 404,
        "error_message": "Page Not Found",
        "error_description": "The page you are looking for does not exist",
        "allowed_types": [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
    }

    return render_template("error.html", **context), 404


def handle_413(error):
    """Handle 413 Request Entity Too Large errors."""
    logger.warning(f"413 error: {error} - URL: {request.url}")

    if request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "File too large",
                    "message": "The uploaded file is too large",
                }
            ),
            413,
        )

    context = {
        "error_code": 413,
        "error_message": "File Too Large",
        "error_description": "The uploaded file exceeds the maximum allowed size",
        "allowed_types": [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
    }

    return render_template("error.html", **context), 413


def handle_500(error):
    """Handle 500 Internal Server Error."""
    logger.error(f"500 error: {error} - URL: {request.url}")

    if request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                }
            ),
            500,
        )

    context = {
        "error_code": 500,
        "error_message": "Internal Server Error",
        "error_description": "An unexpected error occurred. Please try again later",
        "allowed_types": [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
    }

    return render_template("error.html", **context), 500


def handle_csrf_error(error):
    """Handle CSRF token errors."""
    logger.warning(f"CSRF error: {error} - URL: {request.url}")

    if request.is_json:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "CSRF token missing or invalid",
                    "message": "Security token validation failed",
                }
            ),
            400,
        )

    context = {
        "error_code": 400,
        "error_message": "Security Error",
        "error_description": "Security token validation failed. Please refresh the page and try again",
        "allowed_types": [
            ".pdf",
            ".docx",
            ".doc",
            ".txt",
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".gif",
        ],
    }

    return render_template("error.html", **context), 400
