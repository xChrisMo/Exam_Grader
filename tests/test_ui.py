"""
UI and Frontend tests for the Exam Grader application.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from webapp.exam_grader_app import app


class TestUI:
    """Test UI functionality and accessibility."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing
        with app.test_client() as client:
            yield client

    def test_dashboard_loads(self, client):
        """Test that dashboard loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"Dashboard" in response.data
        assert b"Exam Grader" in response.data

    def test_dashboard_accessibility(self, client):
        """Test dashboard accessibility features."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for ARIA labels
        assert "aria-labelledby" in html
        assert "aria-label" in html
        assert "role=" in html

        # Check for semantic HTML
        assert "<main" in html
        assert "<nav" in html
        assert "<header" in html

        # Check for proper heading structure
        assert "<h1" in html
        assert "<h3" in html

    def test_responsive_meta_tags(self, client):
        """Test responsive design meta tags."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        assert "viewport" in html
        assert "width=device-width" in html
        assert "initial-scale=1.0" in html

    def test_security_headers(self, client):
        """Test security headers in HTML."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for security meta tags
        assert "X-Content-Type-Options" in html
        assert "X-Frame-Options" in html
        assert "X-XSS-Protection" in html
        assert "Referrer-Policy" in html

    def test_upload_guide_page(self, client):
        """Test upload guide page loads."""
        response = client.get("/upload-guide")
        assert response.status_code == 200
        assert b"Upload Marking Guide" in response.data

    def test_upload_submission_page(self, client):
        """Test upload submission page loads."""
        response = client.get("/upload-submission")
        assert response.status_code == 200
        assert b"Upload Submission" in response.data

    def test_settings_page(self, client):
        """Test settings page loads."""
        response = client.get("/settings")
        assert response.status_code == 200
        assert b"Settings" in response.data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # Healthy or unhealthy
        assert response.content_type == "application/json"

        data = response.get_json()
        assert "status" in data
        assert "timestamp" in data

    def test_error_pages(self, client):
        """Test error page handling."""
        # Test 404 page
        response = client.get("/nonexistent-page")
        assert response.status_code == 404

        # Test that error page contains helpful information
        html = response.data.decode("utf-8")
        assert "not found" in html.lower() or "404" in html

    def test_navigation_links(self, client):
        """Test navigation links are present."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for main navigation links
        assert "Dashboard" in html
        assert "Upload Guide" in html
        assert "Upload Submission" in html
        assert "Settings" in html

    def test_flash_message_structure(self, client):
        """Test flash message HTML structure."""
        # This would need to be tested with actual flash messages
        # For now, just check the template structure
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for flash message container
        assert "flash-message" in html or "flash-messages" in html

    def test_form_accessibility(self, client):
        """Test form accessibility features."""
        response = client.get("/upload-guide")
        html = response.data.decode("utf-8")

        # Check for proper form labels
        assert "<label" in html
        assert "for=" in html

        # Check for form validation attributes
        assert "required" in html or "aria-required" in html

    def test_css_and_js_loading(self, client):
        """Test that CSS and JS files are referenced."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for CSS files
        assert "tailwindcss" in html
        assert "custom.css" in html

        # Check for JS files
        assert "app.js" in html

    def test_mobile_friendly_elements(self, client):
        """Test mobile-friendly design elements."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for mobile navigation
        assert "lg:hidden" in html  # Mobile menu toggle

        # Check for responsive grid classes
        assert "md:grid-cols" in html or "lg:grid-cols" in html

    def test_loading_states(self, client):
        """Test loading state elements are present."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for loading-related classes
        assert "animate-" in html or "loading" in html or "spinner" in html

    def test_icon_accessibility(self, client):
        """Test that icons have proper accessibility attributes."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for aria-hidden on decorative icons
        assert 'aria-hidden="true"' in html

    def test_color_contrast_classes(self, client):
        """Test that proper color contrast classes are used."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for proper text color classes
        assert "text-gray-900" in html  # Dark text
        assert "text-white" in html  # White text on dark backgrounds

        # Check for proper background colors
        assert "bg-white" in html
        assert "bg-primary" in html or "bg-blue" in html


class TestJavaScriptIntegration:
    """Test JavaScript integration and functionality."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.test_client() as client:
            yield client

    def test_javascript_namespace(self, client):
        """Test that JavaScript namespace is properly defined."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for ExamGrader namespace
        assert "ExamGrader" in html

    def test_api_endpoints_defined(self, client):
        """Test that API endpoints are defined in JavaScript."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for API endpoint definitions
        assert "apiEndpoints" in html or "/api/" in html

    def test_error_handling_functions(self, client):
        """Test that error handling functions are present."""
        response = client.get("/")
        html = response.data.decode("utf-8")

        # Check for error handling functions
        assert "showToast" in html or "displayMessage" in html
        assert "error" in html


if __name__ == "__main__":
    pytest.main([__file__])
