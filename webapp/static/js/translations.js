// Initialize translation system
window.ExamGrader = window.ExamGrader || {};
ExamGrader.translations = ExamGrader.translations || {};
ExamGrader.currentLang = ExamGrader.currentLang || 'en';

// Translation system with proper structure
ExamGrader.translations = {
    // English translations
    'en': {
        // Auth
        'welcome_back': 'Welcome back',
        'sign_in_to_continue': 'Sign in to continue',
        'username': 'Username',
        'password': 'Password',
        'remember_me': 'Remember me',
        'forgot_password': 'Forgot your password?',
        'sign_in': 'Sign in',
        'dont_have_account': "Don't have an account?",
        'sign_up_here': 'Sign up here',
        'back_to_homepage': '← Back to homepage',
        'please_enter_credentials': 'Please enter username and password.',
        'signing_in': 'Signing in...',
        'enter_your_username': 'Enter your username',
        'enter_your_password': 'Enter your password',
        'create_account_title': 'Create Your Account',
        'create_account_subtitle': 'Join thousands of educators using AI-powered grading',
        'email_address': 'Email Address',
        'choose_username': 'Choose a username',
        'username_requirements': 'At least 3 characters, letters, numbers, hyphens, and underscores only',
        'enter_email': 'Enter your email address',
        'choose_password': 'Choose a password',
        'password_requirements': 'At least 8 characters, including uppercase, lowercase, numbers, and special characters',
        'create_strong_password': 'Create a strong password',
        'confirm_password': 'Confirm Password',
        'confirm_your_password': 'Confirm your password',
        'i_agree_to': 'I agree to the',
        'terms_and_conditions': 'Terms and Conditions',
        'and': 'and',
        'privacy_policy': 'Privacy Policy',
        'create_account_button': 'Create Account',
        'already_have_account': 'Already have an account?',
        'sign_in_here': 'Sign in here',
        'creating_account': 'Creating Account...',
        
        // Common UI elements
        'app_title': 'Exam Grader',
        'dashboard': 'Dashboard',
        'settings': 'Settings',
        'upload': 'Upload',
        'download': 'Download',
        'save': 'Save',
        'cancel': 'Cancel',
        'delete': 'Delete',
        'edit': 'Edit',
        'view': 'View',
        'search': 'Search',
        'filter': 'Filter',
        'sort': 'Sort',
        'loading': 'Loading...',
        'processing': 'Processing...',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Information',
        
        // Navigation
        'nav_dashboard': 'Dashboard',
        'nav_exams': 'Exams',
        'nav_marking_guides': 'Marking Guides',
        'nav_submissions': 'Submissions',
        'nav_results': 'Results',
        'nav_settings': 'Settings',
        'nav_logout': 'Logout',
        
        // System Status
        'system_status': 'System Status',
        'ocr_service': 'OCR Service',
        'ai_service': 'AI Service',
        'status_online': 'Online',
        'status_offline': 'Offline',
        'status_limited': 'Limited',
        'all_services_ready': 'All services ready',
        'some_services_offline': 'Some services offline',
        
        // Dashboard
        'guide_status': 'Guide Status',
        'status_uploaded': 'Uploaded',
        'status_not_uploaded': 'Not uploaded',
        'ready_to_grade': 'Ready to grade',
        'upload_required': 'Upload required',
        'submissions': 'Submissions',
        'processed': 'processed',
        'last_score': 'Last Score',
        'latest_result': 'Latest result',
        'no_grades': 'No grades yet',
        'marking_guide': 'Marking Guide',
        'upload_marking_guide': 'Upload marking guide',
        
        // Upload Submission
        'upload_submissions_title': 'Upload Student Submissions',
        'upload_submissions_description': 'Upload student submissions to be graded against your marking guide. Supports both single file and batch processing for multiple files.',
        'marking_guide_required': 'Marking Guide Required',
        'marking_guide_required_description': 'You need to upload a marking guide before you can submit student work for grading.',
        'upload_mode': 'Upload Mode',
        'single_file': 'Single File',
        'multiple_files': 'Multiple Files (Batch)',
        'student_submission_file': 'Student Submission File',
        'upload_a_file': 'Upload a file',
        'or_drag_and_drop': 'or drag and drop',
        'file_types_hint': 'PDF, Word documents, or images up to 16MB',
        'selected_files': 'Selected Files',
        'clear_all_files': 'Clear All Files',
        'total_size': 'Total size',
        
        // Upload Guide
        'upload_marking_guide_title': 'Upload Marking Guide',
        'upload_marking_guide_description': 'Upload your marking guide to enable automated grading. Supported formats: PDF, Word documents, and images.',
        'marking_guide_file': 'Marking Guide File',
        'uploading_processing': 'Uploading and processing...',
        'back_to_dashboard': 'Back to Dashboard',
        'upload_guide_button': 'Upload Guide',
        'tips_for_best_results': 'Tips for best results',
        'tip_structure': 'Ensure your marking guide is clearly structured with question numbers and point values',
        'tip_quality': 'Use high-quality scans or images if uploading image files',
        'tip_format': 'PDF and Word documents typically provide the best OCR results',
        'tip_answers': 'Include sample answers or key points for each question when possible',
        'please_select_file': 'Please select a file to upload.',
        'upload_failed': 'Upload failed. Please try again.',
        
        // Settings page
        'settings_title': 'Application Settings',
        'settings_description': 'Configure your exam grader application preferences and settings.',
        'file_upload_settings': 'File Upload Settings',
        'max_file_size': 'File Processing (Unlimited)',
        'max_file_size_description': 'No file size limits - unlimited processing enabled',
        'allowed_file_formats': 'Allowed File Formats',
        'allowed_formats_description': 'Select which file formats are allowed for upload',
        'processing_settings': 'Processing Settings',
        'auto_process': 'Auto-process submissions',
        'auto_process_description': 'Automatically start processing when files are uploaded',
        'save_temp_files': 'Save temporary files',
        'save_temp_files_description': 'Keep temporary files for debugging purposes',
        'ui_settings': 'User Interface Settings',
        'notification_level': 'Notification Level',
        'notification_level_description': 'Choose which notifications to display',
        'theme': 'Theme',
        'theme_description': 'Select your preferred theme',
        'language': 'Language',
        'language_description': 'Choose your preferred language',
        'ai_settings': 'AI Configuration Settings',
        'llm_api_key': 'LLM API Key',
        'llm_api_key_description': 'API key for the LLM service',
        'llm_model': 'LLM Model',
        'llm_model_description': 'Model name for the LLM service (e.g., gpt-3.5-turbo)',
        'save_settings': 'Save Settings',
        
        // Theme options
        'theme_light': 'Light',
        'theme_dark': 'Dark',
        'theme_auto': 'Auto (System)',
        
        // Language options
        'language_en': 'English',
        'language_es': 'Spanish',
        'language_fr': 'French',
        'language_de': 'German',
        'language_zh': 'Chinese',
        
        // Notification levels
        'notification_all': 'All Notifications',
        'notification_important': 'Important Only',
        'notification_minimal': 'Minimal',
        'notification_none': 'None'
    },
    
    // Spanish translations
    'es': {
        // Auth
        'welcome_back': 'Bienvenido de nuevo',
        'sign_in_to_continue': 'Inicia sesión para continuar',
        'username': 'Nombre de usuario',
        'password': 'Contraseña',
        'remember_me': 'Recordarme',
        'forgot_password': '¿Olvidaste tu contraseña?',
        'sign_in': 'Iniciar sesión',
        'dont_have_account': '¿No tienes una cuenta?',
        'sign_up_here': 'Regístrate aquí',
        'back_to_homepage': '← Volver a la página principal',
        'please_enter_credentials': 'Por favor, introduce nombre de usuario y contraseña.',
        'signing_in': 'Iniciando sesión...',
        'enter_your_username': 'Introduce tu nombre de usuario',
        'enter_your_password': 'Introduce tu contraseña',
        'create_account_title': 'Crea tu cuenta',
        'create_account_subtitle': 'Únete a miles de educadores que utilizan calificación con IA',
        'email_address': 'Dirección de correo electrónico',
        'choose_username': 'Elige un nombre de usuario',
        'username_requirements': 'Al menos 3 caracteres, solo letras, números, guiones y guiones bajos',
        'enter_email': 'Introduce tu dirección de correo electrónico',
        'choose_password': 'Elige una contraseña',
        'password_requirements': 'Al menos 8 caracteres, incluyendo mayúsculas, minúsculas, números y caracteres especiales',
        'create_strong_password': 'Crea una contraseña segura',
        'confirm_password': 'Confirmar contraseña',
        'confirm_your_password': 'Confirma tu contraseña',
        'i_agree_to': 'Acepto los',
        'terms_and_conditions': 'Términos y condiciones',
        'and': 'y',
        'privacy_policy': 'Política de privacidad',
        'create_account_button': 'Crear cuenta',
        'already_have_account': '¿Ya tienes una cuenta?',
        'sign_in_here': 'Inicia sesión aquí',
        'creating_account': 'Creando cuenta...',
        
        // Common UI elements
        'app_title': 'Calificador de Exámenes',
        'dashboard': 'Panel',
        'settings': 'Configuración',
        'upload': 'Subir',
        'download': 'Descargar',
        'save': 'Guardar',
        'cancel': 'Cancelar',
        'delete': 'Eliminar',
        'edit': 'Editar',
        'view': 'Ver',
        'search': 'Buscar',
        'filter': 'Filtrar',
        'sort': 'Ordenar',
        'loading': 'Cargando...',
        'processing': 'Procesando...',
        'success': 'Éxito',
        'error': 'Error',
        'warning': 'Advertencia',
        'info': 'Información',
        
        // Navigation
        'nav_dashboard': 'Panel',
        'nav_exams': 'Exámenes',
        'nav_marking_guides': 'Guías de Calificación',
        'nav_submissions': 'Entregas',
        'nav_results': 'Resultados',
        'nav_settings': 'Configuración',
        'nav_logout': 'Cerrar Sesión',
        
        // System Status
        'system_status': 'Estado del Sistema',
        'ocr_service': 'Servicio OCR',
        'ai_service': 'Servicio de IA',
        'status_online': 'En línea',
        'status_offline': 'Fuera de línea',
        'status_limited': 'Limitado',
        'all_services_ready': 'Todos los servicios listos',
        'some_services_offline': 'Algunos servicios fuera de línea',
        
        // Dashboard
        'guide_status': 'Estado de la Guía',
        'status_uploaded': 'Subida',
        'status_not_uploaded': 'No subida',
        'ready_to_grade': 'Listo para calificar',
        'upload_required': 'Subida requerida',
        'submissions': 'Entregas',
        'processed': 'procesadas',
        'last_score': 'Última Calificación',
        'latest_result': 'Resultado más reciente',
        'no_grades': 'Sin calificaciones aún',
        'marking_guide': 'Guía de Calificación',
        'upload_marking_guide': 'Subir guía de calificación',
        
        // Upload Submission
        'upload_submissions_title': 'Subir Entregas de Estudiantes',
        'upload_submissions_description': 'Sube las entregas de los estudiantes para ser calificadas según tu guía de calificación. Admite procesamiento de archivos individuales y por lotes.',
        'marking_guide_required': 'Guía de Calificación Requerida',
        'marking_guide_required_description': 'Necesitas subir una guía de calificación antes de poder enviar trabajos de estudiantes para calificar.',
        'upload_mode': 'Modo de Carga',
        'single_file': 'Archivo Único',
        'multiple_files': 'Múltiples Archivos (Lote)',
        'student_submission_file': 'Archivo de Entrega del Estudiante',
        'upload_a_file': 'Subir un archivo',
        'or_drag_and_drop': 'o arrastrar y soltar',
        'file_types_hint': 'PDF, documentos Word o imágenes de hasta 16MB',
        'selected_files': 'Archivos Seleccionados',
        'clear_all_files': 'Borrar Todos los Archivos',
        'total_size': 'Tamaño total',
        
        // Upload Guide
        'upload_marking_guide_title': 'Subir Guía de Calificación',
        'upload_marking_guide_description': 'Sube tu guía de calificación para habilitar la calificación automatizada. Formatos admitidos: PDF, documentos Word e imágenes.',
        'marking_guide_file': 'Archivo de Guía de Calificación',
        'uploading_processing': 'Subiendo y procesando...',
        'back_to_dashboard': 'Volver al Panel',
        'upload_guide_button': 'Subir Guía',
        'tips_for_best_results': 'Consejos para mejores resultados',
        'tip_structure': 'Asegúrate de que tu guía de calificación esté claramente estructurada con números de pregunta y valores de puntos',
        'tip_quality': 'Utiliza escaneos o imágenes de alta calidad si subes archivos de imagen',
        'tip_format': 'Los documentos PDF y Word suelen proporcionar los mejores resultados de OCR',
        'tip_answers': 'Incluye respuestas de ejemplo o puntos clave para cada pregunta cuando sea posible',
        'please_select_file': 'Por favor, selecciona un archivo para subir.',
        'upload_failed': 'Error al subir. Por favor, inténtalo de nuevo.',
        
        // Settings page
        'settings_title': 'Configuración de la Aplicación',
        'settings_description': 'Configure las preferencias y ajustes de su aplicación de calificación de exámenes.',
        'file_upload_settings': 'Configuración de Carga de Archivos',
        'max_file_size': 'Procesamiento de Archivos (Ilimitado)',
        'max_file_size_description': 'Sin límites de tamaño de archivo - procesamiento ilimitado habilitado',
        'allowed_file_formats': 'Formatos de Archivo Permitidos',
        'allowed_formats_description': 'Seleccione qué formatos de archivo están permitidos para cargar',
        'processing_settings': 'Configuración de Procesamiento',
        'auto_process': 'Procesar automáticamente las entregas',
        'auto_process_description': 'Iniciar automáticamente el procesamiento cuando se cargan archivos',
        'save_temp_files': 'Guardar archivos temporales',
        'save_temp_files_description': 'Mantener archivos temporales para fines de depuración',
        'ui_settings': 'Configuración de Interfaz de Usuario',
        'notification_level': 'Nivel de Notificación',
        'notification_level_description': 'Elija qué notificaciones mostrar',
        'theme': 'Tema',
        'theme_description': 'Seleccione su tema preferido',
        'language': 'Idioma',
        'language_description': 'Elija su idioma preferido',
        'ai_settings': 'Configuración de IA',
        'llm_api_key': 'Clave API LLM',
        'llm_api_key_description': 'Clave API para el servicio LLM',
        'llm_model': 'Modelo LLM',
        'llm_model_description': 'Nombre del modelo para el servicio LLM (ej., gpt-3.5-turbo)',
        'save_settings': 'Guardar Configuración',
        
        // Theme options
        'theme_light': 'Claro',
        'theme_dark': 'Oscuro',
        'theme_auto': 'Automático (Sistema)',
        
        // Language options
        'language_en': 'Inglés',
        'language_es': 'Español',
        'language_fr': 'Francés',
        'language_de': 'Alemán',
        'language_zh': 'Chino',
        
        // Notification levels
        'notification_all': 'Todas las Notificaciones',
        'notification_important': 'Solo Importantes',
        'notification_minimal': 'Mínimas',
        'notification_none': 'Ninguna'
    }
};

// Translation function
ExamGrader.translate = function(key) {
    const lang = this.currentLang || 'en';
    return this.translations[lang] && this.translations[lang][key] ||
           this.translations.en[key] ||  // Fallback to English
           key;  // Fallback to key if not found
};

// Function to change language
ExamGrader.setLanguage = function(language) {
    this.currentLang = language;
    // Save to localStorage if available
    if (typeof localStorage !== 'undefined') {
        localStorage.setItem('examGraderLanguage', language);
    }
};

// Function to get current language
ExamGrader.getCurrentLanguage = function() {
    return this.currentLang || 'en';
};

// Initialize language from localStorage if available
if (typeof localStorage !== 'undefined') {
    const savedLang = localStorage.getItem('examGraderLanguage');
    if (savedLang) {
        ExamGrader.currentLang = savedLang;
    }
}