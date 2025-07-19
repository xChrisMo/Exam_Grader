/**
 * Settings Manager for Exam Grader Application
 * Handles applying UI settings like theme and language
 */

// Settings namespace
const SettingsManager = {
    // Current language
    currentLanguage: 'en',
    
    // Apply theme based on saved setting
    applyTheme: function() {
        // Get theme from localStorage or fallback to server-side setting
        const storedTheme = localStorage.getItem('theme');
        const theme = storedTheme || document.documentElement.getAttribute('data-theme') || 'light';
        
        // Apply theme to HTML element
        document.documentElement.setAttribute('data-theme', theme);
        document.body.setAttribute('data-theme', theme);
        
        // Apply appropriate class to body
        if (theme === 'dark') {
            document.documentElement.classList.add('dark');
            document.documentElement.classList.remove('light');
        } else {
            document.documentElement.classList.add('light');
            document.documentElement.classList.remove('dark');
        }
        
        console.log(`Theme applied: ${theme}`);
    },
    
    // Apply language based on saved setting
    applyLanguage: function() {
        // Get language from localStorage or fallback to server-side setting
        const storedLanguage = localStorage.getItem('language');
        const language = storedLanguage || document.documentElement.getAttribute('lang') || 'en';
        
        // Apply language to HTML element
        document.documentElement.setAttribute('lang', language);
        this.currentLanguage = language;
        
        // Apply translations to all elements with data-i18n attribute
        this.translatePage();
        
        console.log(`Language applied: ${language}`);
    },
    
    // Translate the page based on current language
    translatePage: function() {
        // Skip if translations are not available
        if (typeof ExamGrader === 'undefined' || !ExamGrader.translations || !ExamGrader.translations[this.currentLanguage]) {
            console.warn('Translations not available for', this.currentLanguage);
            return;
        }
        
        // Get the translation dictionary for current language
        const dictionary = ExamGrader.translations[this.currentLanguage];
        
        // Find all elements with data-i18n attribute
        const elements = document.querySelectorAll('[data-i18n]');
        
        // Update text content for each element
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            if (dictionary[key]) {
                element.textContent = dictionary[key];
            }
        });
        
        // Update placeholders for input elements
        const inputElements = document.querySelectorAll('input[data-i18n-placeholder]');
        inputElements.forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            if (dictionary[key]) {
                element.placeholder = dictionary[key];
            }
        });
        
        // Update titles/tooltips
        const titleElements = document.querySelectorAll('[data-i18n-title]');
        titleElements.forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            if (dictionary[key]) {
                element.title = dictionary[key];
            }
        });
    },
    
    // Save settings to localStorage when changed
    saveSettings: function() {
        // Listen for changes to notification level
        const notificationLevelSelect = document.getElementById('notification_level');
        if (notificationLevelSelect) {
            notificationLevelSelect.addEventListener('change', function() {
                localStorage.setItem('notification_level', this.value);
                console.log(`Notification level saved: ${this.value}`);
            });
        }
        
        // Listen for changes to theme
        const themeSelect = document.getElementById('theme');
        if (themeSelect) {
            themeSelect.addEventListener('change', function() {
                localStorage.setItem('theme', this.value);
                SettingsManager.applyTheme();
                console.log(`Theme saved: ${this.value}`);
            });
        }
        
        // Listen for changes to language
        const languageSelect = document.getElementById('language');
        if (languageSelect) {
            languageSelect.addEventListener('change', function() {
                localStorage.setItem('language', this.value);
                SettingsManager.currentLanguage = this.value;
                SettingsManager.applyLanguage();
                // Force page reload to ensure all content is translated
                // This is needed because some content might be dynamically generated
                // or not have data-i18n attributes
                window.location.reload();
                console.log(`Language saved: ${this.value}`);
            });
        }
    },
    
    // Initialize settings
    init: function() {
        // Get current language first
        const storedLanguage = localStorage.getItem('language');
        this.currentLanguage = storedLanguage || document.documentElement.getAttribute('lang') || 'en';
        
        // Apply saved settings
        this.applyTheme();
        this.applyLanguage();
        
        // Set up event listeners for settings changes
        this.saveSettings();
        
        // Apply settings immediately when settings page loads
        const settingsForm = document.getElementById('settings-form');
        if (settingsForm) {
            // Update form values from localStorage if available
            const notificationLevel = localStorage.getItem('notification_level');
            const theme = localStorage.getItem('theme');
            const language = localStorage.getItem('language');
            
            if (notificationLevel) {
                const notificationSelect = document.getElementById('notification_level');
                if (notificationSelect) notificationSelect.value = notificationLevel;
            }
            
            if (theme) {
                const themeSelect = document.getElementById('theme');
                if (themeSelect) themeSelect.value = theme;
            }
            
            if (language) {
                const languageSelect = document.getElementById('language');
                if (languageSelect) languageSelect.value = language;
            }
        }
        
        // Apply translations to the page
        this.translatePage();
        
        console.log('Settings manager initialized');
    }
};

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", function() {
    SettingsManager.init();
});