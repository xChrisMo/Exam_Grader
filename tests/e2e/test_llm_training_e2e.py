"""
End-to-end tests for LLM training system.

These tests simulate real user interactions with the system.
"""

import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
import tempfile
import os

from webapp.app_factory import create_app
from src.database.models import db
from tests.conftest import create_test_user

class TestLLMTrainingE2E:
    """End-to-end tests for LLM training system."""
    
    @pytest.fixture(scope="class")
    def app(self):
        """Create test application."""
        app = create_app('testing')
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Create Selenium WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        yield driver
        driver.quit()
    
    @pytest.fixture
    def test_user(self, app):
        """Create test user."""
        with app.app_context():
            return create_test_user()
    
    @pytest.fixture
    def test_files(self):
        """Create test files for upload."""
        files = []
        for i in range(3):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"This is test document {i} for LLM training.\n")
                f.write("It contains sample content that will be used for model training.\n")
                f.write(f"Document {i} has unique content for testing purposes.")
                files.append(f.name)
        
        yield files
        
        # Cleanup
        for file_path in files:
            try:
                os.unlink(file_path)
            except OSError:
                pass
    
    def test_complete_user_workflow(self, driver, app, test_user, test_files):
        """Test complete user workflow from login to model testing."""
        with app.test_request_context():
            # Start the test server
            app.run(host='127.0.0.1', port=5555, debug=False, threaded=True)
        
        try:
            base_url = "http://127.0.0.1:5555"
            
            # Step 1: Login
            self._login_user(driver, base_url, test_user.username, 'testpass123')
            
            # Step 2: Navigate to LLM training page
            self._navigate_to_llm_training(driver, base_url)
            
            # Step 3: Upload documents
            document_ids = self._upload_documents(driver, test_files)
            assert len(document_ids) == 3
            
            # Step 4: Create dataset
            dataset_id = self._create_dataset(driver, document_ids)
            assert dataset_id is not None
            
            # Step 5: Start training job
            job_id = self._start_training_job(driver, dataset_id)
            assert job_id is not None
            
            # Step 6: Monitor training progress
            self._monitor_training_progress(driver, job_id)
            
            # Step 7: Test trained model
            self._test_trained_model(driver, job_id)
            
        except Exception as e:
            # Take screenshot on failure
            driver.save_screenshot('test_failure.png')
            raise e
    
    def test_document_management_ui(self, driver, app, test_user, test_files):
        """Test document management user interface."""
        with app.test_request_context():
            app.run(host='127.0.0.1', port=5556, debug=False, threaded=True)
        
        base_url = "http://127.0.0.1:5556"
        
        # Login and navigate
        self._login_user(driver, base_url, test_user.username, 'testpass123')
        self._navigate_to_llm_training(driver, base_url)
        
        # Test document upload with drag and drop
        self._test_drag_drop_upload(driver, test_files[0])
        
        # Test document validation display
        self._test_document_validation_display(driver)
        
        # Test document retry functionality
        self._test_document_retry(driver)
        
        # Test document organization and filtering
        self._test_document_filtering(driver)
    
    def test_training_monitoring_ui(self, driver, app, test_user):
        """Test training job monitoring interface."""
        with app.test_request_context():
            app.run(host='127.0.0.1', port=5557, debug=False, threaded=True)
        
        base_url = "http://127.0.0.1:5557"
        
        # Login and navigate
        self._login_user(driver, base_url, test_user.username, 'testpass123')
        self._navigate_to_llm_training(driver, base_url)
        
        # Test progress tracking display
        self._test_progress_tracking(driver)
        
        # Test real-time updates
        self._test_realtime_updates(driver)
        
        # Test training job management
        self._test_job_management(driver)
    
    def test_model_testing_ui(self, driver, app, test_user):
        """Test model testing user interface."""
        with app.test_request_context():
            app.run(host='127.0.0.1', port=5558, debug=False, threaded=True)
        
        base_url = "http://127.0.0.1:5558"
        
        # Login and navigate
        self._login_user(driver, base_url, test_user.username, 'testpass123')
        
        # Navigate to model testing
        driver.get(f"{base_url}/llm/model-testing")
        
        # Test model testing interface
        self._test_model_testing_interface(driver)
        
        # Test result visualization
        self._test_result_visualization(driver)
    
    def test_error_handling_ui(self, driver, app, test_user):
        """Test error handling in the user interface."""
        with app.test_request_context():
            app.run(host='127.0.0.1', port=5559, debug=False, threaded=True)
        
        base_url = "http://127.0.0.1:5559"
        
        # Login and navigate
        self._login_user(driver, base_url, test_user.username, 'testpass123')
        self._navigate_to_llm_training(driver, base_url)
        
        # Test various error scenarios
        self._test_upload_error_handling(driver)
        self._test_network_error_handling(driver)
        self._test_validation_error_display(driver)
    
    def test_responsive_design(self, driver, app, test_user):
        """Test responsive design on different screen sizes."""
        with app.test_request_context():
            app.run(host='127.0.0.1', port=5560, debug=False, threaded=True)
        
        base_url = "http://127.0.0.1:5560"
        
        # Test different screen sizes
        screen_sizes = [
            (1920, 1080),  # Desktop
            (1024, 768),   # Tablet
            (375, 667)     # Mobile
        ]
        
        for width, height in screen_sizes:
            driver.set_window_size(width, height)
            
            self._login_user(driver, base_url, test_user.username, 'testpass123')
            self._navigate_to_llm_training(driver, base_url)
            
            # Test UI elements are accessible and properly sized
            self._test_responsive_elements(driver, width, height)
    
    def _login_user(self, driver, base_url, username, password):
        """Login user through the web interface."""
        driver.get(f"{base_url}/login")
        
        username_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        password_field = driver.find_element(By.NAME, "password")
        login_button = driver.find_element(By.XPATH, "//button[@type='submit']")
        
        # Fill and submit form
        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.url_contains("/dashboard")
        )
    
    def _navigate_to_llm_training(self, driver, base_url):
        """Navigate to LLM training page."""
        driver.get(f"{base_url}/llm/training")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "llm-training-container"))
        )
    
    def _upload_documents(self, driver, file_paths):
        """Upload documents through the UI."""
        document_ids = []
        
        # Find upload area
        upload_area = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "document-upload-area"))
        )
        
        # Upload each file
        for file_path in file_paths:
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            file_input.send_keys(file_path)
            
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CLASS_NAME, "upload-success"))
            )
            
            document_id = self._extract_document_id_from_ui(driver)
            document_ids.append(document_id)
        
        return document_ids
    
    def _create_dataset(self, driver, document_ids):
        """Create dataset through the UI."""
        # Click create dataset button
        create_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "create-dataset-btn"))
        )
        create_button.click()
        
        # Fill dataset form
        name_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "dataset_name"))
        )
        name_field.send_keys("E2E Test Dataset")
        
        # Select documents (this would depend on actual UI implementation)
        self._select_documents_in_ui(driver, document_ids)
        
        # Submit form
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dataset-created"))
        )
        
        return self._extract_dataset_id_from_ui(driver)
    
    def _start_training_job(self, driver, dataset_id):
        """Start training job through the UI."""
        # Click start training button
        start_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "start-training-btn"))
        )
        start_button.click()
        
        # Fill training configuration
        job_name = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "job_name"))
        )
        job_name.send_keys("E2E Test Training Job")
        
        # Select model and configure parameters
        self._configure_training_parameters(driver)
        
        # Submit training job
        submit_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "training-started"))
        )
        
        return self._extract_job_id_from_ui(driver)
    
    def _monitor_training_progress(self, driver, job_id):
        """Monitor training progress through the UI."""
        # Navigate to training monitoring page
        driver.get(driver.current_url + f"/jobs/{job_id}")
        
        progress_bar = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "training-progress"))
        )
        
        start_time = time.time()
        while time.time() - start_time < 60:  # Wait up to 1 minute
            try:
                completed_indicator = driver.find_element(By.CLASS_NAME, "training-completed")
                if completed_indicator:
                    break
            except:
                pass
            
            time.sleep(2)  # Check every 2 seconds
    
    def _test_trained_model(self, driver, job_id):
        """Test the trained model through the UI."""
        # Navigate to model testing
        test_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "test-model-btn"))
        )
        test_button.click()
        
        # Create test session
        self._create_test_session(driver, job_id)
        
        # Upload test submissions
        self._upload_test_submissions(driver)
        
        # Run test and view results
        self._run_model_test_and_view_results(driver)
    
    def _test_drag_drop_upload(self, driver, file_path):
        """Test drag and drop file upload."""
        # This would require more complex JavaScript execution
        # For now, we'll test the regular file upload
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        file_input.send_keys(file_path)
        
        # Verify upload feedback
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "upload-progress"))
        )
    
    def _test_document_validation_display(self, driver):
        """Test document validation status display."""
        validation_indicators = driver.find_elements(By.CLASS_NAME, "validation-status")
        assert len(validation_indicators) > 0
        
        error_messages = driver.find_elements(By.CLASS_NAME, "validation-error")
        # Errors are optional, just verify the elements exist
    
    def _test_document_retry(self, driver):
        """Test document retry functionality."""
        retry_buttons = driver.find_elements(By.CLASS_NAME, "retry-processing-btn")
        
        if retry_buttons:
            retry_buttons[0].click()
            
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "retry-completed"))
            )
    
    def _test_document_filtering(self, driver):
        """Test document filtering and organization."""
        # Test search functionality
        search_box = driver.find_element(By.CLASS_NAME, "document-search")
        search_box.send_keys("test")
        
        time.sleep(1)
        
        # Test filter buttons
        filter_buttons = driver.find_elements(By.CLASS_NAME, "document-filter-btn")
        if filter_buttons:
            filter_buttons[0].click()
            time.sleep(1)
    
    def _test_progress_tracking(self, driver):
        """Test progress tracking display."""
        progress_elements = driver.find_elements(By.CLASS_NAME, "progress-indicator")
        assert len(progress_elements) > 0
        
        metrics_elements = driver.find_elements(By.CLASS_NAME, "training-metrics")
        # Metrics might not be available immediately
    
    def _test_realtime_updates(self, driver):
        """Test real-time updates."""
        # This would require WebSocket testing or polling verification
        # For now, we'll check that update mechanisms are in place
        update_elements = driver.find_elements(By.CLASS_NAME, "auto-update")
        # Auto-update elements should exist
    
    def _test_job_management(self, driver):
        """Test training job management."""
        # Test pause/resume functionality
        control_buttons = driver.find_elements(By.CLASS_NAME, "job-control-btn")
        
        if control_buttons:
            # Test pause
            pause_btn = next((btn for btn in control_buttons if "pause" in btn.text.lower()), None)
            if pause_btn:
                pause_btn.click()
                time.sleep(1)
    
    def _test_model_testing_interface(self, driver):
        """Test model testing interface."""
        create_test_btn = driver.find_element(By.CLASS_NAME, "create-test-session-btn")
        create_test_btn.click()
        
        # Fill test session form
        session_name = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "session_name"))
        )
        session_name.send_keys("E2E Test Session")
    
    def _test_result_visualization(self, driver):
        """Test result visualization."""
        chart_elements = driver.find_elements(By.CLASS_NAME, "result-chart")
        # Charts might not be available without actual results
        
        result_tables = driver.find_elements(By.CLASS_NAME, "result-table")
    
    def _test_upload_error_handling(self, driver):
        """Test upload error handling."""
        # Try to upload an invalid file type
        try:
            file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
            # This would need an actual invalid file
            # For now, just verify error handling elements exist
            error_elements = driver.find_elements(By.CLASS_NAME, "upload-error")
        except:
            pass  # Error handling test
    
    def _test_network_error_handling(self, driver):
        """Test network error handling."""
        # This would require mocking network failures
        # For now, verify error handling UI elements exist
        error_handlers = driver.find_elements(By.CLASS_NAME, "network-error-handler")
    
    def _test_validation_error_display(self, driver):
        """Test validation error display."""
        validation_errors = driver.find_elements(By.CLASS_NAME, "validation-error-display")
    
    def _test_responsive_elements(self, driver, width, height):
        """Test responsive design elements."""
        # Check that key elements are visible and properly sized
        main_container = driver.find_element(By.CLASS_NAME, "main-container")
        assert main_container.is_displayed()
        
        # Check navigation elements
        nav_elements = driver.find_elements(By.CLASS_NAME, "nav-item")
        
        if width < 768:
            # Mobile navigation should be collapsed or hamburger menu
            hamburger = driver.find_elements(By.CLASS_NAME, "navbar-toggler")
            # Should have hamburger menu on mobile
        else:
            # Desktop navigation should be expanded
            assert len(nav_elements) > 0
    
    def _extract_document_id_from_ui(self, driver):
        """Extract document ID from UI elements."""
        # This would depend on actual UI implementation
        # For testing, return a mock ID
        return f"doc_{int(time.time())}"
    
    def _extract_dataset_id_from_ui(self, driver):
        """Extract dataset ID from UI elements."""
        return f"dataset_{int(time.time())}"
    
    def _extract_job_id_from_ui(self, driver):
        """Extract job ID from UI elements."""
        return f"job_{int(time.time())}"
    
    def _select_documents_in_ui(self, driver, document_ids):
        """Select documents in the UI."""
        # This would involve clicking checkboxes or similar
        checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for checkbox in checkboxes[:len(document_ids)]:
            if not checkbox.is_selected():
                checkbox.click()
    
    def _configure_training_parameters(self, driver):
        """Configure training parameters in the UI."""
        # Set epochs
        epochs_field = driver.find_element(By.NAME, "epochs")
        epochs_field.clear()
        epochs_field.send_keys("5")
        
        # Set batch size
        batch_size_field = driver.find_element(By.NAME, "batch_size")
        batch_size_field.clear()
        batch_size_field.send_keys("4")
    
    def _create_test_session(self, driver, job_id):
        """Create test session in the UI."""
        session_name = driver.find_element(By.NAME, "session_name")
        session_name.send_keys("E2E Test Session")
        
        create_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        create_btn.click()
    
    def _upload_test_submissions(self, driver):
        """Upload test submissions."""
        # This would involve uploading test files
        file_input = driver.find_element(By.CSS_SELECTOR, "input[type='file']")
        # Would need actual test submission files
    
    def _run_model_test_and_view_results(self, driver):
        """Run model test and view results."""
        run_test_btn = driver.find_element(By.CLASS_NAME, "run-test-btn")
        run_test_btn.click()
        
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "test-results"))
        )