/**
 * Form Components Library
 * Provides comprehensive form components with validation, accessibility, and responsive design
 * Integrates with existing UI components and follows Tailwind CSS patterns
 */

class FormComponents {
    constructor(options = {}) {
        this.options = {
            validateOnBlur: true,
            validateOnInput: false,
            showValidationIcons: true,
            animateValidation: true,
            ...options
        };
        
        this.validators = new Map();
        this.forms = new Map();
        this.fieldStates = new Map();
        
        this.init();
    }
    
    init() {
        this.setupGlobalStyles();
        this.registerDefaultValidators();
        this.bindGlobalEvents();
    }
    
    setupGlobalStyles() {
        const styles = `
            /* Form Component Styles */
            .form-field {
                @apply mb-4;
            }
            
            .form-label {
                @apply block text-sm font-medium text-gray-700 mb-1;
            }
            
            .form-label.required::after {
                content: ' *';
                @apply text-red-500;
            }
            
            .form-input {
                @apply block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm;
                @apply focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500;
                @apply transition-colors duration-200;
            }
            
            .form-input:disabled {
                @apply bg-gray-50 text-gray-500 cursor-not-allowed;
            }
            
            .form-input.error {
                @apply border-red-500 focus:ring-red-500 focus:border-red-500;
            }
            
            .form-input.success {
                @apply border-green-500 focus:ring-green-500 focus:border-green-500;
            }
            
            .form-textarea {
                @apply form-input resize-vertical min-h-[100px];
            }
            
            .form-select {
                @apply form-input pr-10 bg-white;
                background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='m6 8 4 4 4-4'/%3e%3c/svg%3e");
                background-position: right 0.5rem center;
                background-repeat: no-repeat;
                background-size: 1.5em 1.5em;
            }
            
            .form-checkbox, .form-radio {
                @apply h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded;
            }
            
            .form-radio {
                @apply rounded-full;
            }
            
            .form-error {
                @apply mt-1 text-sm text-red-600;
            }
            
            .form-help {
                @apply mt-1 text-sm text-gray-500;
            }
            
            .form-group {
                @apply space-y-4;
            }
            
            .form-row {
                @apply grid grid-cols-1 gap-4;
            }
            
            .form-row.cols-2 {
                @apply md:grid-cols-2;
            }
            
            .form-row.cols-3 {
                @apply md:grid-cols-3;
            }
            
            .form-row.cols-4 {
                @apply md:grid-cols-4;
            }
            
            .form-actions {
                @apply flex flex-col sm:flex-row gap-3 pt-6 border-t border-gray-200;
            }
            
            .form-actions.right {
                @apply sm:justify-end;
            }
            
            .form-actions.center {
                @apply sm:justify-center;
            }
            
            .form-actions.between {
                @apply sm:justify-between;
            }
            
            .input-group {
                @apply relative;
            }
            
            .input-addon {
                @apply absolute inset-y-0 flex items-center px-3 text-gray-500;
            }
            
            .input-addon.left {
                @apply left-0;
            }
            
            .input-addon.right {
                @apply right-0;
            }
            
            .input-group .form-input.has-left-addon {
                @apply pl-10;
            }
            
            .input-group .form-input.has-right-addon {
                @apply pr-10;
            }
            
            .form-validation-icon {
                @apply absolute right-3 top-1/2 transform -translate-y-1/2 w-5 h-5;
            }
            
            .form-validation-icon.success {
                @apply text-green-500;
            }
            
            .form-validation-icon.error {
                @apply text-red-500;
            }
            
            /* Mobile optimizations */
            @media (max-width: 640px) {
                .form-input, .form-select, .form-textarea {
                    @apply text-base; /* Prevent iOS zoom */
                }
                
                .form-actions {
                    @apply flex-col;
                }
                
                .form-row {
                    @apply grid-cols-1;
                }
            }
            
            /* Animation classes */
            .form-animate-in {
                animation: formSlideIn 0.3s ease-out;
            }
            
            .form-animate-out {
                animation: formSlideOut 0.3s ease-in;
            }
            
            @keyframes formSlideIn {
                from {
                    opacity: 0;
                    transform: translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            
            @keyframes formSlideOut {
                from {
                    opacity: 1;
                    transform: translateY(0);
                }
                to {
                    opacity: 0;
                    transform: translateY(-10px);
                }
            }
            
            /* Focus visible for keyboard navigation */
            .form-input:focus-visible,
            .form-select:focus-visible,
            .form-textarea:focus-visible {
                @apply ring-2 ring-blue-500 ring-offset-2;
            }
            
            /* High contrast mode support */
            @media (prefers-contrast: high) {
                .form-input, .form-select, .form-textarea {
                    @apply border-2 border-gray-900;
                }
                
                .form-input:focus, .form-select:focus, .form-textarea:focus {
                    @apply ring-4 ring-blue-600;
                }
            }
        `;
        
        this.injectStyles(styles);
    }
    
    injectStyles(styles) {
        const styleSheet = document.createElement('style');
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }
    
    registerDefaultValidators() {
        // Required validator
        this.addValidator('required', (value, options = {}) => {
            const isEmpty = value === null || value === undefined || 
                           (typeof value === 'string' && value.trim() === '') ||
                           (Array.isArray(value) && value.length === 0);
            return {
                valid: !isEmpty,
                message: options.message || 'This field is required'
            };
        });
        
        // Email validator
        this.addValidator('email', (value, options = {}) => {
            if (!value) return { valid: true }; // Optional field
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return {
                valid: emailRegex.test(value),
                message: options.message || 'Please enter a valid email address'
            };
        });
        
        // Length validator
        this.addValidator('length', (value, options = {}) => {
            if (!value) return { valid: true }; // Optional field
            const length = value.length;
            const { min, max } = options;
            
            if (min !== undefined && length < min) {
                return {
                    valid: false,
                    message: options.message || `Minimum ${min} characters required`
                };
            }
            
            if (max !== undefined && length > max) {
                return {
                    valid: false,
                    message: options.message || `Maximum ${max} characters allowed`
                };
            }
            
            return { valid: true };
        });
        
        // Pattern validator
        this.addValidator('pattern', (value, options = {}) => {
            if (!value) return { valid: true }; // Optional field
            const pattern = new RegExp(options.pattern);
            return {
                valid: pattern.test(value),
                message: options.message || 'Invalid format'
            };
        });
        
        // Number validator
        this.addValidator('number', (value, options = {}) => {
            if (!value) return { valid: true }; // Optional field
            const num = parseFloat(value);
            
            if (isNaN(num)) {
                return {
                    valid: false,
                    message: options.message || 'Please enter a valid number'
                };
            }
            
            const { min, max } = options;
            
            if (min !== undefined && num < min) {
                return {
                    valid: false,
                    message: options.message || `Minimum value is ${min}`
                };
            }
            
            if (max !== undefined && num > max) {
                return {
                    valid: false,
                    message: options.message || `Maximum value is ${max}`
                };
            }
            
            return { valid: true };
        });
        
        // File validator
        this.addValidator('file', (files, options = {}) => {
            if (!files || files.length === 0) {
                return { valid: true }; // Optional field
            }
            
            const { maxSize, allowedTypes, maxFiles } = options;
            
            if (maxFiles && files.length > maxFiles) {
                return {
                    valid: false,
                    message: options.message || `Maximum ${maxFiles} files allowed`
                };
            }
            
            for (let file of files) {
                if (maxSize && file.size > maxSize) {
                    return {
                        valid: false,
                        message: options.message || `File size must be less than ${this.formatFileSize(maxSize)}`
                    };
                }
                
                if (allowedTypes && allowedTypes.length > 0) {
                    const extension = '.' + file.name.split('.').pop().toLowerCase();
                    if (!allowedTypes.includes(extension)) {
                        return {
                            valid: false,
                            message: options.message || `Allowed file types: ${allowedTypes.join(', ')}`
                        };
                    }
                }
            }
            
            return { valid: true };
        });
    }
    
    addValidator(name, validatorFn) {
        this.validators.set(name, validatorFn);
    }
    
    createForm(container, options = {}) {
        const formId = options.id || `form-${Date.now()}`;
        const form = {
            id: formId,
            container: typeof container === 'string' ? document.querySelector(container) : container,
            fields: new Map(),
            options: {
                validateOnSubmit: true,
                preventSubmitOnError: true,
                showSuccessMessage: false,
                ...options
            }
        };
        
        this.forms.set(formId, form);
        this.setupFormEvents(form);
        
        return formId;
    }
    
    addField(formId, fieldConfig) {
        const form = this.forms.get(formId);
        if (!form) {
            throw new Error(`Form with ID ${formId} not found`);
        }
        
        const field = this.createField(fieldConfig);
        form.fields.set(field.name, field);
        form.container.appendChild(field.element);
        
        this.setupFieldEvents(field, form);
        
        return field;
    }
    
    createField(config) {
        const {
            type = 'text',
            name,
            label,
            placeholder,
            value = '',
            required = false,
            disabled = false,
            readonly = false,
            help,
            validators = [],
            options = [], // For select, radio, checkbox groups
            rows = 4, // For textarea
            multiple = false, // For select and file inputs
            accept, // For file inputs
            addon, // For input groups
            className = '',
            attributes = {}
        } = config;
        
        const fieldId = `field-${name}-${Date.now()}`;
        const fieldWrapper = document.createElement('div');
        fieldWrapper.className = `form-field ${className}`;
        
        // Create label
        if (label) {
            const labelEl = document.createElement('label');
            labelEl.htmlFor = fieldId;
            labelEl.className = `form-label ${required ? 'required' : ''}`;
            labelEl.textContent = label;
            fieldWrapper.appendChild(labelEl);
        }
        
        // Create input container
        const inputContainer = document.createElement('div');
        inputContainer.className = addon ? 'input-group' : 'relative';
        
        // Create input element
        let inputEl;
        
        switch (type) {
            case 'textarea':
                inputEl = document.createElement('textarea');
                inputEl.rows = rows;
                inputEl.className = 'form-textarea';
                break;
                
            case 'select':
                inputEl = document.createElement('select');
                inputEl.className = 'form-select';
                inputEl.multiple = multiple;
                
                // Add options
                options.forEach(option => {
                    const optionEl = document.createElement('option');
                    optionEl.value = option.value || option;
                    optionEl.textContent = option.label || option;
                    if (option.selected) optionEl.selected = true;
                    inputEl.appendChild(optionEl);
                });
                break;
                
            case 'checkbox':
            case 'radio':
                if (options.length > 0) {
                    // Multiple checkboxes/radios
                    const groupContainer = document.createElement('div');
                    groupContainer.className = 'space-y-2';
                    
                    options.forEach((option, index) => {
                        const optionWrapper = document.createElement('div');
                        optionWrapper.className = 'flex items-center';
                        
                        const optionInput = document.createElement('input');
                        optionInput.type = type;
                        optionInput.id = `${fieldId}-${index}`;
                        optionInput.name = name;
                        optionInput.value = option.value || option;
                        optionInput.className = `form-${type}`;
                        if (option.checked) optionInput.checked = true;
                        
                        const optionLabel = document.createElement('label');
                        optionLabel.htmlFor = `${fieldId}-${index}`;
                        optionLabel.className = 'ml-2 text-sm text-gray-700';
                        optionLabel.textContent = option.label || option;
                        
                        optionWrapper.appendChild(optionInput);
                        optionWrapper.appendChild(optionLabel);
                        groupContainer.appendChild(optionWrapper);
                    });
                    
                    inputContainer.appendChild(groupContainer);
                    inputEl = groupContainer; // For event handling
                } else {
                    // Single checkbox/radio
                    inputEl = document.createElement('input');
                    inputEl.type = type;
                    inputEl.className = `form-${type}`;
                }
                break;
                
            case 'file':
                inputEl = document.createElement('input');
                inputEl.type = 'file';
                inputEl.className = 'form-input file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100';
                inputEl.multiple = multiple;
                if (accept) inputEl.accept = accept;
                break;
                
            default:
                inputEl = document.createElement('input');
                inputEl.type = type;
                inputEl.className = 'form-input';
                break;
        }
        
        // Set common attributes
        if (inputEl.tagName !== 'DIV') { // Skip for checkbox/radio groups
            inputEl.id = fieldId;
            inputEl.name = name;
            if (placeholder) inputEl.placeholder = placeholder;
            if (value && type !== 'file') inputEl.value = value;
            inputEl.disabled = disabled;
            inputEl.readOnly = readonly;
            
            // Add custom attributes
            Object.entries(attributes).forEach(([key, val]) => {
                inputEl.setAttribute(key, val);
            });
        }
        
        // Add addon if specified
        if (addon) {
            const addonEl = document.createElement('div');
            addonEl.className = `input-addon ${addon.position || 'left'}`;
            
            if (addon.icon) {
                addonEl.innerHTML = addon.icon;
            } else if (addon.text) {
                addonEl.textContent = addon.text;
            }
            
            inputContainer.appendChild(addonEl);
            
            if (inputEl.tagName !== 'DIV') {
                inputEl.classList.add(`has-${addon.position || 'left'}-addon`);
            }
        }
        
        if (inputEl.tagName !== 'DIV') {
            inputContainer.appendChild(inputEl);
        }
        
        // Add validation icon container
        if (this.options.showValidationIcons && type !== 'checkbox' && type !== 'radio') {
            const iconContainer = document.createElement('div');
            iconContainer.className = 'form-validation-icon hidden';
            iconContainer.setAttribute('aria-hidden', 'true');
            inputContainer.appendChild(iconContainer);
        }
        
        fieldWrapper.appendChild(inputContainer);
        
        // Add help text
        if (help) {
            const helpEl = document.createElement('div');
            helpEl.className = 'form-help';
            helpEl.textContent = help;
            fieldWrapper.appendChild(helpEl);
        }
        
        // Add error container
        const errorEl = document.createElement('div');
        errorEl.className = 'form-error hidden';
        errorEl.setAttribute('role', 'alert');
        errorEl.setAttribute('aria-live', 'polite');
        fieldWrapper.appendChild(errorEl);
        
        return {
            name,
            type,
            element: fieldWrapper,
            input: inputEl,
            error: errorEl,
            validators,
            required,
            config
        };
    }
    
    setupFormEvents(form) {
        const formEl = form.container.querySelector('form') || form.container;
        
        formEl.addEventListener('submit', (e) => {
            if (form.options.validateOnSubmit) {
                const isValid = this.validateForm(form.id);
                if (!isValid && form.options.preventSubmitOnError) {
                    e.preventDefault();
                    this.focusFirstError(form.id);
                }
            }
        });
    }
    
    setupFieldEvents(field, form) {
        const input = field.input;
        
        if (input.tagName === 'DIV') {
            // Handle checkbox/radio groups
            const inputs = input.querySelectorAll('input');
            inputs.forEach(inp => {
                this.addFieldEventListeners(inp, field, form);
            });
        } else {
            this.addFieldEventListeners(input, field, form);
        }
    }
    
    addFieldEventListeners(input, field, form) {
        if (this.options.validateOnBlur) {
            input.addEventListener('blur', () => {
                this.validateField(form.id, field.name);
            });
        }
        
        if (this.options.validateOnInput) {
            const eventType = input.type === 'file' ? 'change' : 'input';
            input.addEventListener(eventType, () => {
                // Debounce validation for input events
                clearTimeout(input.validationTimeout);
                input.validationTimeout = setTimeout(() => {
                    this.validateField(form.id, field.name);
                }, 300);
            });
        }
    }
    
    validateField(formId, fieldName) {
        const form = this.forms.get(formId);
        const field = form.fields.get(fieldName);
        
        if (!field) return true;
        
        const value = this.getFieldValue(field);
        const errors = [];
        
        // Run validators
        for (const validatorConfig of field.validators) {
            const validatorName = typeof validatorConfig === 'string' ? validatorConfig : validatorConfig.type;
            const validatorOptions = typeof validatorConfig === 'object' ? validatorConfig : {};
            
            const validator = this.validators.get(validatorName);
            if (validator) {
                const result = validator(value, validatorOptions);
                if (!result.valid) {
                    errors.push(result.message);
                    break; // Stop at first error
                }
            }
        }
        
        this.displayFieldValidation(field, errors);
        
        return errors.length === 0;
    }
    
    validateForm(formId) {
        const form = this.forms.get(formId);
        let isValid = true;
        
        for (const [fieldName] of form.fields) {
            const fieldValid = this.validateField(formId, fieldName);
            if (!fieldValid) {
                isValid = false;
            }
        }
        
        return isValid;
    }
    
    getFieldValue(field) {
        const input = field.input;
        
        if (input.tagName === 'DIV') {
            // Handle checkbox/radio groups
            const inputs = input.querySelectorAll('input');
            if (field.type === 'checkbox') {
                return Array.from(inputs)
                    .filter(inp => inp.checked)
                    .map(inp => inp.value);
            } else {
                const checked = Array.from(inputs).find(inp => inp.checked);
                return checked ? checked.value : null;
            }
        }
        
        switch (field.type) {
            case 'file':
                return input.files;
            case 'checkbox':
                return input.checked;
            case 'number':
                return input.value ? parseFloat(input.value) : null;
            default:
                return input.value;
        }
    }
    
    setFieldValue(formId, fieldName, value) {
        const form = this.forms.get(formId);
        const field = form.fields.get(fieldName);
        
        if (!field) return;
        
        const input = field.input;
        
        if (input.tagName === 'DIV') {
            // Handle checkbox/radio groups
            const inputs = input.querySelectorAll('input');
            if (field.type === 'checkbox') {
                const values = Array.isArray(value) ? value : [value];
                inputs.forEach(inp => {
                    inp.checked = values.includes(inp.value);
                });
            } else {
                inputs.forEach(inp => {
                    inp.checked = inp.value === value;
                });
            }
        } else {
            switch (field.type) {
                case 'checkbox':
                    input.checked = Boolean(value);
                    break;
                case 'file':
                    // Cannot set file input value for security reasons
                    break;
                default:
                    input.value = value || '';
                    break;
            }
        }
    }
    
    displayFieldValidation(field, errors) {
        const input = field.input;
        const errorEl = field.error;
        const iconEl = field.element.querySelector('.form-validation-icon');
        
        // Remove existing validation classes
        if (input.tagName !== 'DIV') {
            input.classList.remove('error', 'success');
        }
        
        if (errors.length > 0) {
            // Show error state
            if (input.tagName !== 'DIV') {
                input.classList.add('error');
            }
            
            errorEl.textContent = errors[0];
            errorEl.classList.remove('hidden');
            
            if (iconEl) {
                iconEl.innerHTML = this.getErrorIcon();
                iconEl.className = 'form-validation-icon error';
            }
            
            if (this.options.animateValidation) {
                errorEl.classList.add('form-animate-in');
            }
        } else {
            // Show success state or clear
            errorEl.classList.add('hidden');
            errorEl.textContent = '';
            
            if (this.getFieldValue(field)) {
                if (input.tagName !== 'DIV') {
                    input.classList.add('success');
                }
                
                if (iconEl) {
                    iconEl.innerHTML = this.getSuccessIcon();
                    iconEl.className = 'form-validation-icon success';
                }
            } else {
                if (iconEl) {
                    iconEl.classList.add('hidden');
                }
            }
        }
    }
    
    focusFirstError(formId) {
        const form = this.forms.get(formId);
        
        for (const [fieldName, field] of form.fields) {
            const errorEl = field.error;
            if (!errorEl.classList.contains('hidden')) {
                const input = field.input.tagName === 'DIV' 
                    ? field.input.querySelector('input')
                    : field.input;
                
                if (input) {
                    input.focus();
                    input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                break;
            }
        }
    }
    
    getFormData(formId) {
        const form = this.forms.get(formId);
        const data = {};
        
        for (const [fieldName, field] of form.fields) {
            data[fieldName] = this.getFieldValue(field);
        }
        
        return data;
    }
    
    setFormData(formId, data) {
        Object.entries(data).forEach(([fieldName, value]) => {
            this.setFieldValue(formId, fieldName, value);
        });
    }
    
    resetForm(formId) {
        const form = this.forms.get(formId);
        
        for (const [fieldName, field] of form.fields) {
            this.setFieldValue(formId, fieldName, '');
            this.displayFieldValidation(field, []);
        }
    }
    
    destroyForm(formId) {
        const form = this.forms.get(formId);
        if (form) {
            form.container.innerHTML = '';
            this.forms.delete(formId);
        }
    }
    
    // Utility methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    getSuccessIcon() {
        return `
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
            </svg>
        `;
    }
    
    getErrorIcon() {
        return `
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
            </svg>
        `;
    }
    
    bindGlobalEvents() {
        // Handle form submission with Enter key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.matches('.form-input, .form-textarea, .form-select')) {
                const form = e.target.closest('form');
                if (form && !e.target.matches('textarea')) {
                    e.preventDefault();
                    form.dispatchEvent(new Event('submit', { cancelable: true }));
                }
            }
        });
        
        // Handle accessibility improvements
        document.addEventListener('focus', (e) => {
            if (e.target.matches('.form-input, .form-textarea, .form-select')) {
                e.target.setAttribute('aria-describedby', 
                    [e.target.id + '-help', e.target.id + '-error']
                        .filter(id => document.getElementById(id.replace(e.target.id + '-', '')))
                        .join(' ')
                );
            }
        }, true);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormComponents;
}

// Global instance
if (typeof window !== 'undefined') {
    window.FormComponents = FormComponents;
    
    // Auto-initialize if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.formComponents = new FormComponents();
        });
    } else {
        window.formComponents = new FormComponents();
    }
}