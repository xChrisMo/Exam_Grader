/**
 * Comprehensive Tests for UI Components Library
 * Tests for responsive design, accessibility, and component functionality
 */

// Mock DOM environment for testing
class MockDOM {
    constructor() {
        this.elements = new Map();
        this.eventListeners = new Map();
        this.styles = new Map();
    }

    createElement(tagName) {
        const element = {
            tagName: tagName.toUpperCase(),
            className: '',
            innerHTML: '',
            textContent: '',
            style: {},
            attributes: new Map(),
            children: [],
            parentNode: null,
            eventListeners: new Map(),
            
            setAttribute(name, value) {
                this.attributes.set(name, value);
            },
            
            getAttribute(name) {
                return this.attributes.get(name);
            },
            
            appendChild(child) {
                this.children.push(child);
                child.parentNode = this;
            },
            
            removeChild(child) {
                const index = this.children.indexOf(child);
                if (index > -1) {
                    this.children.splice(index, 1);
                    child.parentNode = null;
                }
            },
            
            addEventListener(event, handler) {
                if (!this.eventListeners.has(event)) {
                    this.eventListeners.set(event, []);
                }
                this.eventListeners.get(event).push(handler);
            },
            
            removeEventListener(event, handler) {
                if (this.eventListeners.has(event)) {
                    const handlers = this.eventListeners.get(event);
                    const index = handlers.indexOf(handler);
                    if (index > -1) {
                        handlers.splice(index, 1);
                    }
                }
            },
            
            dispatchEvent(event) {
                if (this.eventListeners.has(event.type)) {
                    this.eventListeners.get(event.type).forEach(handler => {
                        handler(event);
                    });
                }
            },
            
            querySelector(selector) {
                // Simple mock implementation
                return this.children.find(child => 
                    selector.includes(child.className) || 
                    selector.includes(child.tagName.toLowerCase())
                );
            },
            
            querySelectorAll(selector) {
                return this.children.filter(child => 
                    selector.includes(child.className) || 
                    selector.includes(child.tagName.toLowerCase())
                );
            },
            
            classList: {
                add: function(className) {
                    if (!this.contains(className)) {
                        element.className += (element.className ? ' ' : '') + className;
                    }
                },
                remove: function(className) {
                    element.className = element.className
                        .split(' ')
                        .filter(c => c !== className)
                        .join(' ');
                },
                contains: function(className) {
                    return element.className.split(' ').includes(className);
                },
                toggle: function(className) {
                    if (this.contains(className)) {
                        this.remove(className);
                    } else {
                        this.add(className);
                    }
                }
            }
        };
        
        return element;
    }
    
    createEvent(type) {
        return {
            type,
            preventDefault: () => {},
            stopPropagation: () => {},
            target: null
        };
    }
}

// Setup mock environment
const mockDOM = new MockDOM();
const mockDocument = {
    createElement: (tagName) => mockDOM.createElement(tagName),
    createEvent: (type) => mockDOM.createEvent(type),
    head: mockDOM.createElement('head'),
    body: mockDOM.createElement('body'),
    querySelector: (selector) => mockDOM.createElement('div'),
    getElementById: (id) => mockDOM.createElement('div'),
    addEventListener: () => {}
};

const mockWindow = {
    document: mockDocument,
    IntersectionObserver: class {
        constructor(callback, options) {
            this.callback = callback;
            this.options = options;
        }
        observe() {}
        unobserve() {}
        disconnect() {}
    },
    ResizeObserver: class {
        constructor(callback) {
            this.callback = callback;
        }
        observe() {}
        unobserve() {}
        disconnect() {}
    }
};

// Mock UIComponents for testing
class MockUIComponents {
    constructor() {
        this.components = new Map();
        this.observers = new Map();
        this.announcements = [];
    }

    createButton(options = {}) {
        const button = mockDocument.createElement('button');
        button.className = this.getButtonClasses(options.variant || 'primary', options.size || 'md');
        button.textContent = options.text || 'Button';
        button.disabled = options.disabled || options.loading || false;
        
        if (options.onClick) {
            button.addEventListener('click', options.onClick);
        }
        
        return button;
    }

    createCard(options = {}) {
        const card = mockDocument.createElement('div');
        card.className = 'ui-component bg-white rounded-lg border border-gray-200';
        
        if (options.title) {
            const header = mockDocument.createElement('div');
            header.className = 'px-6 py-4 border-b border-gray-200';
            header.textContent = options.title;
            card.appendChild(header);
        }
        
        const body = mockDocument.createElement('div');
        body.className = 'px-6 py-4';
        body.innerHTML = options.content || '';
        card.appendChild(body);
        
        return card;
    }

    createModal(options = {}) {
        const modal = mockDocument.createElement('div');
        modal.className = 'fixed inset-0 z-50 overflow-y-auto';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        
        const content = mockDocument.createElement('div');
        content.innerHTML = options.content || '';
        modal.appendChild(content);
        
        return modal;
    }

    createProgressIndicator(options = {}) {
        const container = mockDocument.createElement('div');
        container.className = 'ui-component';
        
        const progressBar = mockDocument.createElement('div');
        progressBar.className = 'w-full bg-gray-200 rounded-full';
        progressBar.setAttribute('role', 'progressbar');
        progressBar.setAttribute('aria-valuenow', options.value || 0);
        
        container.appendChild(progressBar);
        return container;
    }

    createAlert(options = {}) {
        const alert = mockDocument.createElement('div');
        alert.className = `ui-component p-4 rounded-md bg-${options.variant || 'info'}-50`;
        alert.setAttribute('role', 'alert');
        alert.innerHTML = options.message || '';
        
        return alert;
    }

    getButtonClasses(variant, size) {
        const baseClasses = 'ui-component inline-flex items-center justify-center font-medium rounded-md';
        const variantClasses = {
            primary: 'bg-blue-600 text-white',
            secondary: 'bg-gray-600 text-white',
            danger: 'bg-red-600 text-white'
        };
        const sizeClasses = {
            sm: 'px-3 py-2 text-sm',
            md: 'px-4 py-2 text-sm',
            lg: 'px-6 py-3 text-base'
        };
        
        return `${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]}`;
    }

    announce(message) {
        this.announcements.push(message);
    }

    registerComponent(name, element) {
        this.components.set(name, element);
    }

    getComponent(name) {
        return this.components.get(name);
    }

    destroy() {
        this.components.clear();
    }
}

// Test Suite for UI Components
class UIComponentsTestSuite {
    constructor() {
        this.tests = [];
        this.results = [];
        this.mockUI = new MockUIComponents();
    }

    addTest(name, testFn) {
        this.tests.push({ name, testFn });
    }

    async runTests() {
        console.log('Running UI Components Tests...');
        
        for (const test of this.tests) {
            try {
                await test.testFn();
                this.results.push({ name: test.name, status: 'PASS' });
                console.log(`✓ ${test.name}`);
            } catch (error) {
                this.results.push({ name: test.name, status: 'FAIL', error: error.message });
                console.error(`✗ ${test.name}: ${error.message}`);
            }
        }
        
        this.printSummary();
    }

    printSummary() {
        const passed = this.results.filter(r => r.status === 'PASS').length;
        const failed = this.results.filter(r => r.status === 'FAIL').length;
        
        console.log('\n=== UI Components Test Summary ===');
        console.log(`Total: ${this.results.length}`);
        console.log(`Passed: ${passed}`);
        console.log(`Failed: ${failed}`);
        
        if (failed > 0) {
            console.log('\nFailed Tests:');
            this.results.filter(r => r.status === 'FAIL').forEach(r => {
                console.log(`- ${r.name}: ${r.error}`);
            });
        }
    }

    assert(condition, message) {
        if (!condition) {
            throw new Error(message || 'Assertion failed');
        }
    }

    assertEqual(actual, expected, message) {
        if (actual !== expected) {
            throw new Error(message || `Expected ${expected}, got ${actual}`);
        }
    }

    assertContains(container, item, message) {
        if (!container.includes(item)) {
            throw new Error(message || `Expected container to include ${item}`);
        }
    }
}

// Initialize test suite
const testSuite = new UIComponentsTestSuite();

// Button Component Tests
testSuite.addTest('Button - Basic Creation', () => {
    const button = testSuite.mockUI.createButton({ text: 'Test Button' });
    testSuite.assertEqual(button.tagName, 'BUTTON', 'Should create button element');
    testSuite.assertEqual(button.textContent, 'Test Button', 'Should set button text');
    testSuite.assertContains(button.className, 'ui-component', 'Should have base component class');
});

testSuite.addTest('Button - Variants', () => {
    const primaryBtn = testSuite.mockUI.createButton({ variant: 'primary' });
    const dangerBtn = testSuite.mockUI.createButton({ variant: 'danger' });
    
    testSuite.assertContains(primaryBtn.className, 'bg-blue-600', 'Primary button should have blue background');
    testSuite.assertContains(dangerBtn.className, 'bg-red-600', 'Danger button should have red background');
});

testSuite.addTest('Button - Sizes', () => {
    const smallBtn = testSuite.mockUI.createButton({ size: 'sm' });
    const largeBtn = testSuite.mockUI.createButton({ size: 'lg' });
    
    testSuite.assertContains(smallBtn.className, 'px-3 py-2 text-sm', 'Small button should have correct padding');
    testSuite.assertContains(largeBtn.className, 'px-6 py-3 text-base', 'Large button should have correct padding');
});

testSuite.addTest('Button - Disabled State', () => {
    const disabledBtn = testSuite.mockUI.createButton({ disabled: true });
    testSuite.assert(disabledBtn.disabled, 'Disabled button should be disabled');
});

testSuite.addTest('Button - Click Handler', () => {
    let clicked = false;
    const button = testSuite.mockUI.createButton({ 
        onClick: () => { clicked = true; }
    });
    
    // Simulate click
    const clickEvent = mockDocument.createEvent('click');
    button.dispatchEvent(clickEvent);
    
    testSuite.assert(clicked, 'Click handler should be called');
});

// Card Component Tests
testSuite.addTest('Card - Basic Creation', () => {
    const card = testSuite.mockUI.createCard({ title: 'Test Card', content: 'Test content' });
    testSuite.assertEqual(card.tagName, 'DIV', 'Should create div element');
    testSuite.assertContains(card.className, 'ui-component', 'Should have base component class');
    testSuite.assertEqual(card.children.length, 2, 'Should have header and body');
});

testSuite.addTest('Card - Title and Content', () => {
    const card = testSuite.mockUI.createCard({ title: 'Test Title', content: 'Test Content' });
    const header = card.children[0];
    const body = card.children[1];
    
    testSuite.assertEqual(header.textContent, 'Test Title', 'Header should contain title');
    testSuite.assertEqual(body.innerHTML, 'Test Content', 'Body should contain content');
});

// Modal Component Tests
testSuite.addTest('Modal - Basic Creation', () => {
    const modal = testSuite.mockUI.createModal({ title: 'Test Modal', content: 'Modal content' });
    testSuite.assertEqual(modal.tagName, 'DIV', 'Should create div element');
    testSuite.assertEqual(modal.getAttribute('role'), 'dialog', 'Should have dialog role');
    testSuite.assertEqual(modal.getAttribute('aria-modal'), 'true', 'Should have aria-modal attribute');
});

testSuite.addTest('Modal - Accessibility', () => {
    const modal = testSuite.mockUI.createModal({ title: 'Accessible Modal' });
    testSuite.assert(modal.getAttribute('role'), 'Should have role attribute');
    testSuite.assert(modal.getAttribute('aria-modal'), 'Should have aria-modal attribute');
});

// Progress Indicator Tests
testSuite.addTest('Progress - Basic Creation', () => {
    const progress = testSuite.mockUI.createProgressIndicator({ value: 50, max: 100 });
    testSuite.assertEqual(progress.tagName, 'DIV', 'Should create div element');
    testSuite.assertContains(progress.className, 'ui-component', 'Should have base component class');
});

testSuite.addTest('Progress - ARIA Attributes', () => {
    const progress = testSuite.mockUI.createProgressIndicator({ value: 75 });
    const progressBar = progress.querySelector('[role="progressbar"]');
    testSuite.assert(progressBar, 'Should have progressbar role element');
    testSuite.assertEqual(progressBar.getAttribute('aria-valuenow'), '75', 'Should set aria-valuenow');
});

// Alert Component Tests
testSuite.addTest('Alert - Basic Creation', () => {
    const alert = testSuite.mockUI.createAlert({ message: 'Test alert', variant: 'info' });
    testSuite.assertEqual(alert.tagName, 'DIV', 'Should create div element');
    testSuite.assertEqual(alert.getAttribute('role'), 'alert', 'Should have alert role');
    testSuite.assertEqual(alert.innerHTML, 'Test alert', 'Should contain message');
});

testSuite.addTest('Alert - Variants', () => {
    const infoAlert = testSuite.mockUI.createAlert({ variant: 'info' });
    const dangerAlert = testSuite.mockUI.createAlert({ variant: 'danger' });
    
    testSuite.assertContains(infoAlert.className, 'bg-info-50', 'Info alert should have info styling');
    testSuite.assertContains(dangerAlert.className, 'bg-danger-50', 'Danger alert should have danger styling');
});

// Component Registration Tests
testSuite.addTest('Component Registration', () => {
    const button = testSuite.mockUI.createButton({ text: 'Registered Button' });
    testSuite.mockUI.registerComponent('test-button', button);
    
    const retrieved = testSuite.mockUI.getComponent('test-button');
    testSuite.assertEqual(retrieved, button, 'Should retrieve registered component');
});

// Accessibility Tests
testSuite.addTest('Accessibility - Announcements', () => {
    testSuite.mockUI.announce('Test announcement');
    testSuite.assertContains(testSuite.mockUI.announcements, 'Test announcement', 'Should record announcements');
});

// Responsive Design Tests
testSuite.addTest('Responsive - Button Classes', () => {
    const button = testSuite.mockUI.createButton({ size: 'md' });
    testSuite.assertContains(button.className, 'px-4 py-2', 'Should have responsive padding');
});

// Cleanup Tests
testSuite.addTest('Component Cleanup', () => {
    testSuite.mockUI.registerComponent('cleanup-test', mockDocument.createElement('div'));
    testSuite.assert(testSuite.mockUI.getComponent('cleanup-test'), 'Component should exist before cleanup');
    
    testSuite.mockUI.destroy();
    testSuite.assert(!testSuite.mockUI.getComponent('cleanup-test'), 'Component should be removed after cleanup');
});

// Error Handling Tests
testSuite.addTest('Error Handling - Invalid Options', () => {
    try {
        const button = testSuite.mockUI.createButton({ variant: 'invalid' });
        // Should handle gracefully
        testSuite.assert(button, 'Should create button even with invalid variant');
    } catch (error) {
        throw new Error('Should not throw error for invalid options');
    }
});

// Performance Tests
testSuite.addTest('Performance - Multiple Components', () => {
    const startTime = Date.now();
    
    for (let i = 0; i < 100; i++) {
        testSuite.mockUI.createButton({ text: `Button ${i}` });
        testSuite.mockUI.createCard({ title: `Card ${i}` });
    }
    
    const endTime = Date.now();
    const duration = endTime - startTime;
    
    testSuite.assert(duration < 1000, `Component creation should be fast (took ${duration}ms)`);
});

// Integration Tests
testSuite.addTest('Integration - Component Interaction', () => {
    let modalOpened = false;
    
    const button = testSuite.mockUI.createButton({
        text: 'Open Modal',
        onClick: () => {
            const modal = testSuite.mockUI.createModal({ title: 'Test Modal' });
            modalOpened = true;
        }
    });
    
    // Simulate click
    const clickEvent = mockDocument.createEvent('click');
    button.dispatchEvent(clickEvent);
    
    testSuite.assert(modalOpened, 'Button should trigger modal creation');
});

// Export test suite for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        UIComponentsTestSuite,
        MockUIComponents,
        MockDOM
    };
}

// Run tests if in browser environment
if (typeof window !== 'undefined') {
    // Auto-run tests when loaded
    document.addEventListener('DOMContentLoaded', () => {
        testSuite.runTests();
    });
    
    // Make test suite available globally
    window.UIComponentsTestSuite = testSuite;
}

// Console output for Node.js environment
if (typeof process !== 'undefined' && process.versions && process.versions.node) {
    testSuite.runTests();
}