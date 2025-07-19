/**
 * State Management System
 * Provides centralized state management with reactive updates, persistence,
 * and integration with UI components
 */

class StateManager {
    constructor(options = {}) {
        this.options = {
            enablePersistence: true,
            persistenceKey: 'exam_grader_state',
            enableDevTools: false,
            enableHistory: true,
            maxHistorySize: 50,
            enableValidation: true,
            enableMiddleware: true,
            ...options
        };
        
        this.state = {};
        this.subscribers = new Map();
        this.middleware = [];
        this.validators = new Map();
        this.history = [];
        this.historyIndex = -1;
        this.isReplaying = false;
        
        this.init();
    }
    
    init() {
        this.setupInitialState();
        this.loadPersistedState();
        this.setupDevTools();
        this.bindEvents();
    }
    
    setupInitialState() {
        this.state = {
            // Application state
            app: {
                isLoading: false,
                error: null,
                notifications: [],
                theme: 'light',
                language: 'en',
                breakpoint: 'lg'
            },
            
            // User state
            user: {
                isAuthenticated: false,
                profile: null,
                preferences: {
                    notifications: true,
                    autoSave: true,
                    theme: 'auto'
                }
            },
            
            // UI state
            ui: {
                sidebar: {
                    isOpen: true,
                    isPinned: false
                },
                modals: {},
                activeTab: null,
                selectedItems: [],
                filters: {},
                sorting: {
                    field: null,
                    direction: 'asc'
                },
                pagination: {
                    page: 1,
                    limit: 20,
                    total: 0
                }
            },
            
            // Form state
            forms: {},
            
            // Data state
            data: {
                submissions: [],
                results: [],
                guides: [],
                cache: {}
            },
            
            // Processing state
            processing: {
                active: {},
                queue: [],
                progress: {},
                results: {}
            },
            
            // WebSocket state
            websocket: {
                connected: false,
                reconnecting: false,
                rooms: [],
                lastMessage: null
            }
        };
    }
    
    loadPersistedState() {
        if (!this.options.enablePersistence) return;
        
        try {
            const persistedState = localStorage.getItem(this.options.persistenceKey);
            if (persistedState) {
                const parsed = JSON.parse(persistedState);
                
                // Merge persisted state with initial state
                this.state = this.deepMerge(this.state, parsed);
            }
        } catch (error) {
            console.warn('Failed to load persisted state:', error);
        }
    }
    
    setupDevTools() {
        if (this.options.enableDevTools && typeof window !== 'undefined') {
            window.__EXAM_GRADER_STATE__ = this;
            
            // Add to Redux DevTools if available
            if (window.__REDUX_DEVTOOLS_EXTENSION__) {
                this.devTools = window.__REDUX_DEVTOOLS_EXTENSION__.connect({
                    name: 'Exam Grader State'
                });
                
                this.devTools.init(this.state);
            }
        }
    }
    
    bindEvents() {
        // Listen for storage changes from other tabs
        if (typeof window !== 'undefined') {
            window.addEventListener('storage', (e) => {
                if (e.key === this.options.persistenceKey && e.newValue) {
                    try {
                        const newState = JSON.parse(e.newValue);
                        this.replaceState(newState, 'STORAGE_SYNC');
                    } catch (error) {
                        console.warn('Failed to sync state from storage:', error);
                    }
                }
            });
        }
        
        // Listen for beforeunload to persist state
        if (typeof window !== 'undefined') {
            window.addEventListener('beforeunload', () => {
                this.persistState();
            });
        }
    }
    
    // Core state methods
    getState(path = null) {
        if (!path) return this.state;
        
        return this.getNestedValue(this.state, path);
    }
    
    setState(path, value, action = 'SET_STATE') {
        if (this.isReplaying) return;
        
        const oldState = this.deepClone(this.state);
        
        // Apply middleware
        if (this.options.enableMiddleware) {
            const middlewareResult = this.applyMiddleware({
                type: action,
                path,
                value,
                oldState,
                newState: this.setNestedValue(this.deepClone(this.state), path, value)
            });
            
            if (middlewareResult === false) {
                return false; // Middleware blocked the update
            }
            
            if (middlewareResult && typeof middlewareResult === 'object') {
                value = middlewareResult.value;
                action = middlewareResult.action || action;
            }
        }
        
        // Validate the change
        if (this.options.enableValidation && !this.validateChange(path, value, oldState)) {
            return false;
        }
        
        // Apply the change
        this.state = this.setNestedValue(this.deepClone(this.state), path, value);
        
        // Add to history
        if (this.options.enableHistory) {
            this.addToHistory({
                action,
                path,
                value,
                oldValue: this.getNestedValue(oldState, path),
                timestamp: Date.now()
            });
        }
        
        // Notify subscribers
        this.notifySubscribers(path, value, oldState);
        
        // Persist state
        if (this.options.enablePersistence) {
            this.persistState();
        }
        
        // Update dev tools
        if (this.devTools) {
            this.devTools.send(action, this.state);
        }
        
        return true;
    }
    
    updateState(path, updater, action = 'UPDATE_STATE') {
        const currentValue = this.getState(path);
        const newValue = typeof updater === 'function' ? updater(currentValue) : updater;
        return this.setState(path, newValue, action);
    }
    
    mergeState(path, value, action = 'MERGE_STATE') {
        const currentValue = this.getState(path);
        const newValue = this.deepMerge(currentValue || {}, value);
        return this.setState(path, newValue, action);
    }
    
    replaceState(newState, action = 'REPLACE_STATE') {
        const oldState = this.deepClone(this.state);
        this.state = newState;
        
        // Notify all subscribers
        this.notifyAllSubscribers(oldState);
        
        // Persist state
        if (this.options.enablePersistence) {
            this.persistState();
        }
        
        // Update dev tools
        if (this.devTools) {
            this.devTools.send(action, this.state);
        }
    }
    
    // Subscription methods
    subscribe(path, callback, options = {}) {
        const id = this.generateId();
        const subscription = {
            id,
            path,
            callback,
            options: {
                immediate: false,
                deep: true,
                ...options
            }
        };
        
        if (!this.subscribers.has(path)) {
            this.subscribers.set(path, new Map());
        }
        
        this.subscribers.get(path).set(id, subscription);
        
        // Call immediately if requested
        if (subscription.options.immediate) {
            callback(this.getState(path), undefined, path);
        }
        
        // Return unsubscribe function
        return () => this.unsubscribe(path, id);
    }
    
    unsubscribe(path, id) {
        if (this.subscribers.has(path)) {
            this.subscribers.get(path).delete(id);
            
            if (this.subscribers.get(path).size === 0) {
                this.subscribers.delete(path);
            }
        }
    }
    
    notifySubscribers(path, value, oldState) {
        // Notify exact path subscribers
        if (this.subscribers.has(path)) {
            const oldValue = this.getNestedValue(oldState, path);
            this.subscribers.get(path).forEach(subscription => {
                if (!subscription.options.deep || !this.deepEqual(value, oldValue)) {
                    subscription.callback(value, oldValue, path);
                }
            });
        }
        
        // Notify parent path subscribers
        const pathParts = path.split('.');
        for (let i = pathParts.length - 1; i > 0; i--) {
            const parentPath = pathParts.slice(0, i).join('.');
            if (this.subscribers.has(parentPath)) {
                const parentValue = this.getState(parentPath);
                const oldParentValue = this.getNestedValue(oldState, parentPath);
                
                this.subscribers.get(parentPath).forEach(subscription => {
                    if (!subscription.options.deep || !this.deepEqual(parentValue, oldParentValue)) {
                        subscription.callback(parentValue, oldParentValue, parentPath);
                    }
                });
            }
        }
        
        // Notify wildcard subscribers
        if (this.subscribers.has('*')) {
            this.subscribers.get('*').forEach(subscription => {
                subscription.callback(this.state, oldState, path);
            });
        }
    }
    
    notifyAllSubscribers(oldState) {
        this.subscribers.forEach((pathSubscribers, path) => {
            if (path === '*') {
                pathSubscribers.forEach(subscription => {
                    subscription.callback(this.state, oldState, '*');
                });
            } else {
                const value = this.getState(path);
                const oldValue = this.getNestedValue(oldState, path);
                
                pathSubscribers.forEach(subscription => {
                    if (!subscription.options.deep || !this.deepEqual(value, oldValue)) {
                        subscription.callback(value, oldValue, path);
                    }
                });
            }
        });
    }
    
    // Middleware methods
    use(middleware) {
        this.middleware.push(middleware);
    }
    
    applyMiddleware(action) {
        let result = action;
        
        for (const middleware of this.middleware) {
            result = middleware(result, this);
            if (result === false) {
                return false; // Stop processing
            }
        }
        
        return result;
    }
    
    // Validation methods
    addValidator(path, validator) {
        if (!this.validators.has(path)) {
            this.validators.set(path, []);
        }
        this.validators.get(path).push(validator);
    }
    
    validateChange(path, value, oldState) {
        if (!this.validators.has(path)) return true;
        
        const validators = this.validators.get(path);
        for (const validator of validators) {
            if (!validator(value, this.getNestedValue(oldState, path), this.state)) {
                return false;
            }
        }
        
        return true;
    }
    
    // History methods
    addToHistory(entry) {
        // Remove future history if we're not at the end
        if (this.historyIndex < this.history.length - 1) {
            this.history = this.history.slice(0, this.historyIndex + 1);
        }
        
        this.history.push(entry);
        
        // Limit history size
        if (this.history.length > this.options.maxHistorySize) {
            this.history = this.history.slice(-this.options.maxHistorySize);
        }
        
        this.historyIndex = this.history.length - 1;
    }
    
    undo() {
        if (this.historyIndex <= 0) return false;
        
        this.isReplaying = true;
        const entry = this.history[this.historyIndex];
        this.setState(entry.path, entry.oldValue, 'UNDO');
        this.historyIndex--;
        this.isReplaying = false;
        
        return true;
    }
    
    redo() {
        if (this.historyIndex >= this.history.length - 1) return false;
        
        this.isReplaying = true;
        this.historyIndex++;
        const entry = this.history[this.historyIndex];
        this.setState(entry.path, entry.value, 'REDO');
        this.isReplaying = false;
        
        return true;
    }
    
    getHistory() {
        return {
            entries: this.history,
            index: this.historyIndex,
            canUndo: this.historyIndex > 0,
            canRedo: this.historyIndex < this.history.length - 1
        };
    }
    
    // Persistence methods
    persistState() {
        if (!this.options.enablePersistence) return;
        
        try {
            // Only persist certain parts of state
            const persistableState = {
                user: this.state.user,
                ui: {
                    sidebar: this.state.ui.sidebar,
                    filters: this.state.ui.filters,
                    sorting: this.state.ui.sorting,
                    pagination: this.state.ui.pagination
                },
                app: {
                    theme: this.state.app.theme,
                    language: this.state.app.language
                }
            };
            
            localStorage.setItem(this.options.persistenceKey, JSON.stringify(persistableState));
        } catch (error) {
            console.warn('Failed to persist state:', error);
        }
    }
    
    clearPersistedState() {
        if (this.options.enablePersistence) {
            localStorage.removeItem(this.options.persistenceKey);
        }
    }
    
    // Form state methods
    createForm(formId, initialData = {}, options = {}) {
        const formState = {
            data: initialData,
            errors: {},
            touched: {},
            isSubmitting: false,
            isValid: true,
            isDirty: false,
            options: {
                validateOnChange: true,
                validateOnBlur: true,
                ...options
            }
        };
        
        this.setState(`forms.${formId}`, formState, 'CREATE_FORM');
        return formId;
    }
    
    updateFormField(formId, fieldName, value) {
        const formPath = `forms.${formId}`;
        const form = this.getState(formPath);
        
        if (!form) return false;
        
        // Update field value
        this.setState(`${formPath}.data.${fieldName}`, value, 'UPDATE_FORM_FIELD');
        
        // Mark as touched
        this.setState(`${formPath}.touched.${fieldName}`, true, 'TOUCH_FORM_FIELD');
        
        // Mark form as dirty
        this.setState(`${formPath}.isDirty`, true, 'MARK_FORM_DIRTY');
        
        // Validate if enabled
        if (form.options.validateOnChange) {
            this.validateFormField(formId, fieldName);
        }
        
        return true;
    }
    
    validateFormField(formId, fieldName) {
        // Implement field validation logic
        const form = this.getState(`forms.${formId}`);
        if (!form) return false;
        
        // Clear existing error
        this.setState(`forms.${formId}.errors.${fieldName}`, null, 'CLEAR_FIELD_ERROR');
        
        // Emit validation event
        document.dispatchEvent(new CustomEvent('state:validate-field', {
            detail: { formId, fieldName, value: form.data[fieldName] }
        }));
        
        return true;
    }
    
    setFormError(formId, fieldName, error) {
        this.setState(`forms.${formId}.errors.${fieldName}`, error, 'SET_FORM_ERROR');
        this.setState(`forms.${formId}.isValid`, false, 'INVALIDATE_FORM');
    }
    
    clearFormErrors(formId) {
        this.setState(`forms.${formId}.errors`, {}, 'CLEAR_FORM_ERRORS');
        this.setState(`forms.${formId}.isValid`, true, 'VALIDATE_FORM');
    }
    
    submitForm(formId) {
        this.setState(`forms.${formId}.isSubmitting`, true, 'SUBMIT_FORM_START');
        
        // Emit submit event
        document.dispatchEvent(new CustomEvent('state:form-submit', {
            detail: { formId, data: this.getState(`forms.${formId}.data`) }
        }));
    }
    
    completeFormSubmission(formId, success = true) {
        this.setState(`forms.${formId}.isSubmitting`, false, 'SUBMIT_FORM_END');
        
        if (success) {
            this.setState(`forms.${formId}.isDirty`, false, 'RESET_FORM_DIRTY');
        }
    }
    
    resetForm(formId, newData = {}) {
        const form = this.getState(`forms.${formId}`);
        if (!form) return false;
        
        this.setState(`forms.${formId}`, {
            ...form,
            data: newData,
            errors: {},
            touched: {},
            isDirty: false,
            isValid: true
        }, 'RESET_FORM');
        
        return true;
    }
    
    destroyForm(formId) {
        const forms = this.getState('forms');
        if (forms && forms[formId]) {
            delete forms[formId];
            this.setState('forms', forms, 'DESTROY_FORM');
        }
    }
    
    // Utility methods
    getNestedValue(obj, path) {
        return path.split('.').reduce((current, key) => {
            return current && current[key] !== undefined ? current[key] : undefined;
        }, obj);
    }
    
    setNestedValue(obj, path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        
        const target = keys.reduce((current, key) => {
            if (!current[key] || typeof current[key] !== 'object') {
                current[key] = {};
            }
            return current[key];
        }, obj);
        
        target[lastKey] = value;
        return obj;
    }
    
    deepClone(obj) {
        if (obj === null || typeof obj !== 'object') return obj;
        if (obj instanceof Date) return new Date(obj.getTime());
        if (obj instanceof Array) return obj.map(item => this.deepClone(item));
        if (typeof obj === 'object') {
            const cloned = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    cloned[key] = this.deepClone(obj[key]);
                }
            }
            return cloned;
        }
        return obj;
    }
    
    deepMerge(target, source) {
        const result = this.deepClone(target);
        
        for (const key in source) {
            if (source.hasOwnProperty(key)) {
                if (source[key] && typeof source[key] === 'object' && !Array.isArray(source[key])) {
                    result[key] = this.deepMerge(result[key] || {}, source[key]);
                } else {
                    result[key] = source[key];
                }
            }
        }
        
        return result;
    }
    
    deepEqual(a, b) {
        if (a === b) return true;
        if (a == null || b == null) return false;
        if (typeof a !== typeof b) return false;
        
        if (typeof a === 'object') {
            if (Array.isArray(a) !== Array.isArray(b)) return false;
            
            const keysA = Object.keys(a);
            const keysB = Object.keys(b);
            
            if (keysA.length !== keysB.length) return false;
            
            for (const key of keysA) {
                if (!keysB.includes(key)) return false;
                if (!this.deepEqual(a[key], b[key])) return false;
            }
            
            return true;
        }
        
        return false;
    }
    
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    }
    
    // Public API helpers
    createSelector(path, transform = (value) => value) {
        return () => transform(this.getState(path));
    }
    
    createAction(type, payloadCreator = (payload) => payload) {
        return (payload) => {
            const action = {
                type,
                payload: payloadCreator(payload),
                timestamp: Date.now()
            };
            
            document.dispatchEvent(new CustomEvent('state:action', {
                detail: action
            }));
            
            return action;
        };
    }
    
    // Cleanup
    destroy() {
        this.persistState();
        this.subscribers.clear();
        this.middleware = [];
        this.validators.clear();
        this.history = [];
        
        if (this.devTools) {
            this.devTools.disconnect();
        }
    }
}

// Built-in middleware
const loggingMiddleware = (action, store) => {
    if (typeof console !== 'undefined' && console.group) {
        console.group(`State Action: ${action.type}`);
        console.log('Path:', action.path);
        console.log('Old Value:', action.oldState ? store.getNestedValue(action.oldState, action.path) : undefined);
        console.log('New Value:', action.value);
        console.log('Full State:', action.newState);
        console.groupEnd();
    }
    return action;
};

const validationMiddleware = (action, store) => {
    // Add custom validation logic here
    return action;
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { StateManager, loggingMiddleware, validationMiddleware };
}

// Global instance
if (typeof window !== 'undefined') {
    window.StateManager = StateManager;
    window.stateManager = new StateManager({
        enableDevTools: true,
        enablePersistence: true
    });
    
    // Add built-in middleware in development
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        window.stateManager.use(loggingMiddleware);
    }
    
    window.stateManager.use(validationMiddleware);
}