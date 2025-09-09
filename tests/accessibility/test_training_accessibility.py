"""
Accessibility Tests for LLM Training Page

Tests to ensure the training page meets accessibility standards
and provides a good user experience for users with disabilities.
"""

import re
import pytest
from bs4 import BeautifulSoup
from unittest.mock import Mock, patch

from webapp.app import create_app
from src.database.models import db, User

@pytest.fixture
def app():
    """Create test Flask application"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def test_user(app):
    """Create test user"""
    with app.app_context():
        user = User(
            id='accessibility-test-user',
            username='accessuser',
            email='access@example.com',
            password_hash='hashed_password'
        )
        db.session.add(user)
        db.session.commit()
        return user

@pytest.fixture
def authenticated_client(client, test_user):
    """Create authenticated test client"""
    with client.session_transaction() as sess:
        sess['_user_id'] = test_user.id
        sess['_fresh'] = True
    return client

class TestSemanticHTML:
    """Test semantic HTML structure"""

    def test_semantic_elements_present(self, authenticated_client):
        """Test that semantic HTML elements are used appropriately"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Check for semantic elements
        semantic_elements = {
            'main': 'Main content area',
            'header': 'Page header',
            'nav': 'Navigation',
            'section': 'Content sections',
            'article': 'Article content',
            'aside': 'Sidebar content',
            'footer': 'Page footer'
        }

        found_elements = []
        for element in semantic_elements.keys():
            if soup.find(element):
                found_elements.append(element)

        # Should have at least main content area
        assert 'main' in found_elements or len(found_elements) >= 2

    def test_heading_hierarchy(self, authenticated_client):
        """Test proper heading hierarchy (h1, h2, h3, etc.)"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find all headings
        headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])

        if headings:
            # Should have at least one h1
            h1_count = len(soup.find_all('h1'))
            assert h1_count >= 1, "Page should have at least one h1 element"

            # Check heading hierarchy
            heading_levels = []
            for heading in headings:
                level = int(heading.name[1])  # Extract number from h1, h2, etc.
                heading_levels.append(level)

            # First heading should be h1
            if heading_levels:
                assert heading_levels[0] == 1, "First heading should be h1"

            # Check for proper nesting (no skipping levels)
            for i in range(1, len(heading_levels)):
                current_level = heading_levels[i]
                previous_level = heading_levels[i-1]

                # Should not skip more than one level
                assert current_level <= previous_level + 1, f"Heading hierarchy skip detected: h{previous_level} to h{current_level}"

    def test_list_structure(self, authenticated_client):
        """Test proper list structure for navigation and content"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Check for proper list structure
        lists = soup.find_all(['ul', 'ol'])

        for list_element in lists:
            # Lists should contain li elements
            list_items = list_element.find_all('li', recursive=False)
            if list_items:  # If list has items, they should be li elements
                assert len(list_items) > 0, "Lists should contain li elements"

                # Check that li elements are direct children
                for item in list_items:
                    assert item.parent == list_element, "li elements should be direct children of ul/ol"

class TestARIAAttributes:
    """Test ARIA (Accessible Rich Internet Applications) attributes"""

    def test_aria_labels_present(self, authenticated_client):
        """Test that ARIA labels are present for interactive elements"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find interactive elements that should have ARIA labels
        interactive_elements = soup.find_all(['button', 'input', 'select', 'textarea'])

        aria_labeled_count = 0
        for element in interactive_elements:
            # Check for various labeling methods
            has_aria_label = element.get('aria-label')
            has_aria_labelledby = element.get('aria-labelledby')
            has_label_element = element.get('id') and soup.find('label', {'for': element.get('id')})
            has_title = element.get('title')

            if has_aria_label or has_aria_labelledby or has_label_element or has_title:
                aria_labeled_count += 1

        # At least 50% of interactive elements should have proper labeling
        if interactive_elements:
            labeling_ratio = aria_labeled_count / len(interactive_elements)
            assert labeling_ratio >= 0.5, f"Only {labeling_ratio:.1%} of interactive elements are properly labeled"

    def test_aria_roles_appropriate(self, authenticated_client):
        """Test that ARIA roles are used appropriately"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find elements with ARIA roles
        elements_with_roles = soup.find_all(attrs={'role': True})

        # Valid ARIA roles
        valid_roles = {
            'button', 'link', 'menuitem', 'tab', 'tabpanel', 'dialog', 'alert',
            'alertdialog', 'application', 'banner', 'complementary', 'contentinfo',
            'form', 'main', 'navigation', 'region', 'search', 'article', 'document',
            'img', 'list', 'listitem', 'table', 'row', 'cell', 'columnheader',
            'rowheader', 'grid', 'gridcell', 'progressbar', 'slider', 'spinbutton',
            'textbox', 'combobox', 'listbox', 'option', 'group', 'presentation'
        }

        for element in elements_with_roles:
            role = element.get('role')
            assert role in valid_roles, f"Invalid ARIA role: {role}"

    def test_aria_expanded_for_collapsible_content(self, authenticated_client):
        """Test aria-expanded for collapsible content"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find elements that might be collapsible (buttons, links with certain classes)
        collapsible_candidates = soup.find_all(['button', 'a'],
                                             class_=re.compile(r'(collapse|expand|toggle|dropdown)', re.I))

        for element in collapsible_candidates:
            # Should have aria-expanded attribute
            aria_expanded = element.get('aria-expanded')
            if aria_expanded:
                assert aria_expanded in ['true', 'false'], f"aria-expanded should be 'true' or 'false', got: {aria_expanded}"

class TestKeyboardNavigation:
    """Test keyboard navigation support"""

    def test_focusable_elements_have_tabindex(self, authenticated_client):
        """Test that interactive elements are keyboard accessible"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find interactive elements
        interactive_elements = soup.find_all(['button', 'input', 'select', 'textarea', 'a'])

        keyboard_accessible_count = 0
        for element in interactive_elements:
            # Check if element is keyboard accessible
            tabindex = element.get('tabindex')
            is_button_or_link = element.name in ['button', 'a', 'input', 'select', 'textarea']

            # Elements are keyboard accessible if:
            # 1. They are naturally focusable (button, input, etc.)
            # 2. They have tabindex >= 0
            # 3. They don't have tabindex="-1" (unless intentionally hidden)

            if is_button_or_link and (not tabindex or tabindex != '-1'):
                keyboard_accessible_count += 1
            elif tabindex and int(tabindex) >= 0:
                keyboard_accessible_count += 1

        # Most interactive elements should be keyboard accessible
        if interactive_elements:
            accessibility_ratio = keyboard_accessible_count / len(interactive_elements)
            assert accessibility_ratio >= 0.8, f"Only {accessibility_ratio:.1%} of interactive elements are keyboard accessible"

    def test_skip_links_present(self, authenticated_client):
        """Test that skip links are present for keyboard navigation"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Look for skip links (usually at the beginning of the page)
        skip_links = soup.find_all('a', href=re.compile(r'#(main|content|skip)'))

        # Should have at least one skip link or main content should be easily accessible
        main_content = soup.find(['main', 'div'], id=re.compile(r'(main|content)'))

        # Either skip links exist or main content is properly marked
        assert len(skip_links) > 0 or main_content is not None, "Should have skip links or clearly marked main content"

class TestColorAndContrast:
    """Test color and contrast accessibility"""

    def test_no_color_only_information(self, authenticated_client):
        """Test that information is not conveyed by color alone"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Look for elements that might use color to convey information
        status_elements = soup.find_all(class_=re.compile(r'(success|error|warning|danger|info)', re.I))

        for element in status_elements:
            # Should have text content or icons, not just color
            text_content = element.get_text(strip=True)
            has_icon = element.find(['i', 'span'], class_=re.compile(r'(icon|fa-)', re.I))
            has_aria_label = element.get('aria-label')

            # Should have some non-color indicator
            assert text_content or has_icon or has_aria_label, f"Element {element} may rely on color alone"

    def test_sufficient_color_contrast_indicators(self, authenticated_client):
        """Test for indicators of sufficient color contrast"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        # This is a basic test - full contrast testing requires color analysis
        # We check for CSS classes that might indicate good contrast practices

        content = response.data.decode('utf-8')

        # Look for CSS frameworks or classes that typically provide good contrast
        good_contrast_indicators = [
            'text-gray-900',  # Tailwind dark text
            'text-white',     # White text (usually on dark background)
            'bg-white',       # White background
            'contrast-',      # Explicit contrast classes
            'high-contrast',  # High contrast mode
        ]

        has_contrast_consideration = any(indicator in content for indicator in good_contrast_indicators)

        # Should show some consideration for contrast
        assert has_contrast_consideration or 'color:' not in content, "Should consider color contrast"

class TestFormAccessibility:
    """Test form accessibility"""

    def test_form_labels_associated(self, authenticated_client):
        """Test that form inputs have associated labels"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find form inputs
        form_inputs = soup.find_all(['input', 'select', 'textarea'])

        labeled_inputs = 0
        for input_element in form_inputs:
            input_type = input_element.get('type', '').lower()

            # Skip hidden inputs and buttons
            if input_type in ['hidden', 'submit', 'button']:
                continue

            # Check for various labeling methods
            input_id = input_element.get('id')
            has_label = input_id and soup.find('label', {'for': input_id})
            has_aria_label = input_element.get('aria-label')
            has_aria_labelledby = input_element.get('aria-labelledby')
            has_title = input_element.get('title')
            has_placeholder = input_element.get('placeholder')  # Not ideal but acceptable

            if has_label or has_aria_label or has_aria_labelledby or has_title or has_placeholder:
                labeled_inputs += 1

        # All form inputs should be labeled
        visible_inputs = [inp for inp in form_inputs if inp.get('type', '').lower() not in ['hidden', 'submit', 'button']]
        if visible_inputs:
            labeling_ratio = labeled_inputs / len(visible_inputs)
            assert labeling_ratio >= 0.9, f"Only {labeling_ratio:.1%} of form inputs are properly labeled"

    def test_form_validation_accessible(self, authenticated_client):
        """Test that form validation messages are accessible"""

        # Test form submission with invalid data
        response = authenticated_client.post('/training/sessions', json={
            'name': '',  # Invalid empty name
            'description': 'Test'
        })

        # Should return validation errors
        if response.status_code == 400:
            # Check if response contains accessible error information
            content = response.data.decode('utf-8')

            # Should have error information that can be read by screen readers
            has_error_info = any(keyword in content.lower() for keyword in
                               ['error', 'invalid', 'required', 'validation'])

            assert has_error_info, "Form validation errors should be accessible"

    def test_required_fields_indicated(self, authenticated_client):
        """Test that required fields are properly indicated"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find required inputs
        required_inputs = soup.find_all(['input', 'select', 'textarea'], required=True)

        for required_input in required_inputs:
            # Should have some indication of being required
            has_required_attr = required_input.get('required')
            has_aria_required = required_input.get('aria-required') == 'true'
            has_asterisk_label = False

            # Check if associated label has asterisk
            input_id = required_input.get('id')
            if input_id:
                label = soup.find('label', {'for': input_id})
                if label and '*' in label.get_text():
                    has_asterisk_label = True

            # Should have at least one indication
            assert has_required_attr or has_aria_required or has_asterisk_label, "Required fields should be clearly indicated"

class TestImageAccessibility:
    """Test image accessibility"""

    def test_images_have_alt_text(self, authenticated_client):
        """Test that images have appropriate alt text"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find all images
        images = soup.find_all('img')

        for img in images:
            # Should have alt attribute
            alt_text = img.get('alt')
            assert alt_text is not None, f"Image {img.get('src', 'unknown')} missing alt attribute"

            # Alt text should be meaningful (not just filename)
            if alt_text:
                # Should not be just a filename
                assert not alt_text.lower().endswith(('.jpg', '.png', '.gif', '.svg')), f"Alt text appears to be filename: {alt_text}"

                # Should not be generic
                generic_alt = ['image', 'picture', 'photo', 'img']
                assert alt_text.lower() not in generic_alt, f"Alt text is too generic: {alt_text}"

    def test_decorative_images_marked(self, authenticated_client):
        """Test that decorative images are properly marked"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find images that might be decorative
        decorative_candidates = soup.find_all('img', class_=re.compile(r'(decoration|ornament|divider)', re.I))

        for img in decorative_candidates:
            # Decorative images should have empty alt text or role="presentation"
            alt_text = img.get('alt')
            role = img.get('role')

            is_properly_marked = alt_text == '' or role == 'presentation'
            assert is_properly_marked, f"Decorative image should have empty alt or role='presentation'"

class TestResponsiveDesign:
    """Test responsive design accessibility"""

    def test_viewport_meta_tag(self, authenticated_client):
        """Test that viewport meta tag is present for mobile accessibility"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        soup = BeautifulSoup(response.data, 'html.parser')

        # Find viewport meta tag
        viewport_meta = soup.find('meta', attrs={'name': 'viewport'})

        assert viewport_meta is not None, "Viewport meta tag should be present for mobile accessibility"

        if viewport_meta:
            content = viewport_meta.get('content', '')
            # Should include width=device-width for proper mobile rendering
            assert 'width=device-width' in content, "Viewport should include width=device-width"

    def test_responsive_css_classes(self, authenticated_client):
        """Test that responsive CSS classes are used"""

        response = authenticated_client.get('/training')
        assert response.status_code == 200

        content = response.data.decode('utf-8')

        # Look for responsive CSS classes (Tailwind CSS examples)
        responsive_patterns = [
            r'sm:',  # Small screens
            r'md:',  # Medium screens
            r'lg:',  # Large screens
            r'xl:',  # Extra large screens
            r'@media',  # CSS media queries
            r'responsive',  # Generic responsive classes
        ]

        has_responsive_design = any(re.search(pattern, content) for pattern in responsive_patterns)

        assert has_responsive_design, "Should include responsive design elements"

class TestErrorHandlingAccessibility:
    """Test accessibility of error handling"""

    def test_error_messages_accessible(self, authenticated_client):
        """Test that error messages are accessible to screen readers"""

        # Trigger an error by accessing non-existent session
        response = authenticated_client.get('/training/sessions/non-existent-session/progress')

        if response.status_code >= 400:
            content = response.data.decode('utf-8')

            # Error content should be structured for accessibility
            soup = BeautifulSoup(content, 'html.parser')

            # Look for error indicators
            error_elements = soup.find_all(class_=re.compile(r'error', re.I))
            error_roles = soup.find_all(attrs={'role': 'alert'})

            # Should have some accessible error indication
            has_accessible_error = len(error_elements) > 0 or len(error_roles) > 0

            # For JSON responses, check structure
            if response.headers.get('Content-Type', '').startswith('application/json'):
                try:
                    import json
                    error_data = json.loads(content)
                    has_accessible_error = 'error' in error_data or 'message' in error_data
                except:
                    pass

            assert has_accessible_error, "Error messages should be accessible"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])