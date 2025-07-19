/**
 * Tests for WebSocket Client
 * 
 * Comprehensive test suite for the unified WebSocket client
 * covering connection management, event handling, reconnection logic,
 * room management, and error scenarios.
 */

// Mock Socket.IO for testing
class MockSocket {
    constructor() {
        this.id = 'mock-session-id';
        this.connected = false;
        this.handlers = new Map();
        this.emittedEvents = [];
        this.shouldFailConnection = false;
        this.shouldFailEmit = false;
    }

    on(event, handler) {
        if (!this.handlers.has(event)) {
            this.handlers.set(event, []);
        }
        this.handlers.get(event).push(handler);
    }

    onAny(handler) {
        this.anyHandler = handler;
    }

    emit(event, data, callback) {
        if (this.shouldFailEmit) {
            throw new Error('Mock emit failure');
        }
        this.emittedEvents.push({ event, data, callback });
        if (callback) {
            setTimeout(() => callback(), 10);
        }
    }

    disconnect() {
        this.connected = false;
        this._trigger('disconnect', 'io client disconnect');
    }

    _trigger(event, ...args) {
        if (this.handlers.has(event)) {
            this.handlers.get(event).forEach(handler => handler(...args));
        }
        if (this.anyHandler && event !== 'connect' && event !== 'disconnect') {
            this.anyHandler(event, ...args);
        }
    }

    _connect() {
        if (this.shouldFailConnection) {
            this._trigger('connect_error', new Error('Mock connection failure'));
            return;
        }
        this.connected = true;
        this._trigger('connect');
    }

    _simulateLatency(latency) {
        this._trigger('pong', latency);
    }

    reset() {
        this.emittedEvents = [];
        this.shouldFailConnection = false;
        this.shouldFailEmit = false;
    }
}

// Mock io function
function mockIo(url, options) {
    const socket = new MockSocket();
    // Simulate async connection
    setTimeout(() => socket._connect(), 10);
    return socket;
}

// Test suite
describe('WebSocketClient', () => {
    let WebSocketClient;
    let originalIo;
    let mockSocket;

    beforeAll(() => {
        // Load the WebSocket client (in a real environment, this would be imported)
        if (typeof require !== 'undefined') {
            WebSocketClient = require('../../webapp/static/js/websocket-client.js');
        } else {
            // Assume it's loaded globally in browser environment
            WebSocketClient = window.WebSocketClient;
        }
    });

    beforeEach(() => {
        // Mock Socket.IO
        originalIo = global.io || window.io;
        global.io = mockIo;
        if (typeof window !== 'undefined') {
            window.io = mockIo;
        }
        
        // Reset mock
        mockSocket = null;
    });

    afterEach(() => {
        // Restore original io
        if (originalIo) {
            global.io = originalIo;
            if (typeof window !== 'undefined') {
                window.io = originalIo;
            }
        } else {
            delete global.io;
            if (typeof window !== 'undefined') {
                delete window.io;
            }
        }
    });

    describe('Initialization', () => {
        test('should initialize with default options', () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            expect(client.options.reconnectAttempts).toBe(10);
            expect(client.options.reconnectDelay).toBe(1000);
            expect(client.options.maxReconnectDelay).toBe(30000);
            expect(client.connectionState).toBe('disconnected');
            expect(client.joinedRooms.size).toBe(0);
            expect(client.messageQueue.length).toBe(0);
        });

        test('should initialize with custom options', () => {
            const options = {
                autoConnect: false,
                reconnectAttempts: 5,
                reconnectDelay: 2000,
                debug: true
            };
            const client = new WebSocketClient(options);
            
            expect(client.options.reconnectAttempts).toBe(5);
            expect(client.options.reconnectDelay).toBe(2000);
            expect(client.options.debug).toBe(true);
        });

        test('should auto-connect when enabled', (done) => {
            const client = new WebSocketClient({ autoConnect: true });
            
            client.onConnect(() => {
                expect(client.isConnected()).toBe(true);
                client.destroy();
                done();
            });
        });
    });

    describe('Connection Management', () => {
        test('should connect successfully', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            const connectPromise = client.connect();
            expect(client.connectionState).toBe('connecting');
            
            await connectPromise;
            expect(client.isConnected()).toBe(true);
            expect(client.stats.totalConnections).toBe(1);
            
            client.destroy();
        });

        test('should handle connection failure', async () => {
            // Mock io to fail
            global.io = () => {
                const socket = new MockSocket();
                socket.shouldFailConnection = true;
                setTimeout(() => socket._connect(), 10);
                return socket;
            };

            const client = new WebSocketClient({ autoConnect: false });
            
            try {
                await client.connect();
                fail('Should have thrown an error');
            } catch (error) {
                expect(client.connectionState).toBe('disconnected');
                expect(client.stats.errors).toBeGreaterThan(0);
            }
            
            client.destroy();
        });

        test('should disconnect properly', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            expect(client.isConnected()).toBe(true);
            
            client.disconnect();
            expect(client.connectionState).toBe('disconnected');
            expect(client.joinedRooms.size).toBe(0);
            
            client.destroy();
        });

        test('should not connect if already connected', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            const secondConnect = await client.connect();
            expect(client.stats.totalConnections).toBe(1);
            
            client.destroy();
        });
    });

    describe('Reconnection Logic', () => {
        test('should attempt reconnection on unexpected disconnect', (done) => {
            const client = new WebSocketClient({ 
                autoConnect: false,
                reconnectDelay: 100,
                debug: true
            });
            
            let reconnectAttempted = false;
            client.onReconnect(() => {
                reconnectAttempted = true;
            });

            client.connect().then(() => {
                // Simulate unexpected disconnect
                client.socket._trigger('disconnect', 'transport close');
                
                setTimeout(() => {
                    expect(reconnectAttempted).toBe(true);
                    expect(client.connectionState).toBe('reconnecting');
                    client.destroy();
                    done();
                }, 150);
            });
        });

        test('should not reconnect on manual disconnect', async () => {
            const client = new WebSocketClient({ 
                autoConnect: false,
                reconnectDelay: 100
            });
            
            let reconnectAttempted = false;
            client.onReconnect(() => {
                reconnectAttempted = true;
            });

            await client.connect();
            client.disconnect();
            
            await new Promise(resolve => setTimeout(resolve, 150));
            expect(reconnectAttempted).toBe(false);
            
            client.destroy();
        });

        test('should use exponential backoff for reconnection', (done) => {
            const client = new WebSocketClient({ 
                autoConnect: false,
                reconnectDelay: 100,
                maxReconnectDelay: 1000
            });
            
            const reconnectTimes = [];
            client.onReconnect((info) => {
                reconnectTimes.push({
                    attempt: info.attempt,
                    delay: info.delay,
                    timestamp: Date.now()
                });
                
                if (info.attempt >= 3) {
                    // Check exponential backoff
                    expect(reconnectTimes[1].delay).toBeGreaterThan(reconnectTimes[0].delay);
                    expect(reconnectTimes[2].delay).toBeGreaterThan(reconnectTimes[1].delay);
                    client.destroy();
                    done();
                }
            });

            // Mock io to always fail
            global.io = () => {
                const socket = new MockSocket();
                socket.shouldFailConnection = true;
                setTimeout(() => socket._connect(), 10);
                return socket;
            };

            client.connect().catch(() => {
                // Expected to fail
            });
        });
    });

    describe('Event Handling', () => {
        test('should register and trigger event handlers', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            let eventReceived = false;
            const testData = { message: 'test' };
            
            client.on('test_event', (data) => {
                eventReceived = true;
                expect(data).toEqual(testData);
            });
            
            // Simulate receiving event
            client.socket._trigger('test_event', testData);
            
            expect(eventReceived).toBe(true);
            expect(client.stats.messagesReceived).toBe(1);
            
            client.destroy();
        });

        test('should remove event handlers', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            let eventCount = 0;
            const handler = () => eventCount++;
            
            client.on('test_event', handler);
            client.socket._trigger('test_event');
            expect(eventCount).toBe(1);
            
            client.off('test_event', handler);
            client.socket._trigger('test_event');
            expect(eventCount).toBe(1); // Should not increment
            
            client.destroy();
        });

        test('should handle connection events', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            let connectInfo = null;
            let disconnectInfo = null;
            
            client.onConnect((info) => {
                connectInfo = info;
            });
            
            client.onDisconnect((info) => {
                disconnectInfo = info;
            });
            
            await client.connect();
            expect(connectInfo).toBeTruthy();
            expect(connectInfo.sessionId).toBe('mock-session-id');
            
            client.disconnect();
            expect(disconnectInfo).toBeTruthy();
            expect(disconnectInfo.reason).toBe('io client disconnect');
            
            client.destroy();
        });
    });

    describe('Message Emission', () => {
        test('should emit messages when connected', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            const testData = { message: 'test' };
            const success = client.emit('test_event', testData);
            
            expect(success).toBe(true);
            expect(client.stats.messagesSent).toBe(1);
            expect(client.socket.emittedEvents).toHaveLength(1);
            expect(client.socket.emittedEvents[0].event).toBe('test_event');
            expect(client.socket.emittedEvents[0].data).toEqual(testData);
            
            client.destroy();
        });

        test('should queue messages when disconnected', () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            const testData = { message: 'test' };
            const success = client.emit('test_event', testData);
            
            expect(success).toBe(false);
            expect(client.messageQueue).toHaveLength(1);
            expect(client.messageQueue[0].event).toBe('test_event');
            expect(client.messageQueue[0].data).toEqual(testData);
            
            client.destroy();
        });

        test('should process queued messages on reconnection', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            // Queue messages while disconnected
            client.emit('test_event1', { id: 1 });
            client.emit('test_event2', { id: 2 });
            expect(client.messageQueue).toHaveLength(2);
            
            // Connect and verify messages are processed
            await client.connect();
            expect(client.messageQueue).toHaveLength(0);
            expect(client.socket.emittedEvents).toHaveLength(2);
            
            client.destroy();
        });

        test('should handle emit errors gracefully', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            // Make emit fail
            client.socket.shouldFailEmit = true;
            
            const success = client.emit('test_event', {});
            expect(success).toBe(false);
            expect(client.stats.errors).toBeGreaterThan(0);
            
            client.destroy();
        });
    });

    describe('Room Management', () => {
        test('should join and leave rooms', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            const roomName = 'test_room';
            
            // Join room
            const joinSuccess = client.joinRoom(roomName);
            expect(joinSuccess).toBe(true);
            expect(client.joinedRooms.has(roomName)).toBe(true);
            
            // Verify join_room event was emitted
            const joinEvent = client.socket.emittedEvents.find(e => e.event === 'join_room');
            expect(joinEvent).toBeTruthy();
            expect(joinEvent.data.room).toBe(roomName);
            
            // Leave room
            const leaveSuccess = client.leaveRoom(roomName);
            expect(leaveSuccess).toBe(true);
            expect(client.joinedRooms.has(roomName)).toBe(false);
            
            client.destroy();
        });

        test('should rejoin rooms after reconnection', async () => {
            const client = new WebSocketClient({ 
                autoConnect: false,
                reconnectDelay: 50
            });
            await client.connect();
            
            const roomName = 'test_room';
            client.joinRoom(roomName);
            client.socket.reset();
            
            // Simulate disconnect and reconnect
            client.socket._trigger('disconnect', 'transport close');
            
            // Wait for reconnection
            await new Promise(resolve => {
                client.onConnect(() => {
                    // Check if room rejoin was attempted
                    const rejoinEvent = client.socket.emittedEvents.find(e => 
                        e.event === 'join_room' && e.data.room === roomName
                    );
                    expect(rejoinEvent).toBeTruthy();
                    resolve();
                });
            });
            
            client.destroy();
        });

        test('should handle progress subscription', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            const sessionId = 'test_session';
            let progressReceived = false;
            
            const callback = (data) => {
                progressReceived = true;
            };
            
            client.subscribeToProgress(sessionId, callback);
            
            // Verify room join
            expect(client.joinedRooms.has(`progress_${sessionId}`)).toBe(true);
            
            // Simulate progress update
            client.socket._trigger('progress_update', { sessionId, progress: 50 });
            expect(progressReceived).toBe(true);
            
            // Unsubscribe
            client.unsubscribeFromProgress(sessionId, callback);
            expect(client.joinedRooms.has(`progress_${sessionId}`)).toBe(false);
            
            client.destroy();
        });
    });

    describe('Statistics and Monitoring', () => {
        test('should track connection statistics', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            const initialStats = client.getStats();
            expect(initialStats.totalConnections).toBe(0);
            expect(initialStats.messagesSent).toBe(0);
            
            await client.connect();
            client.emit('test', {});
            
            const updatedStats = client.getStats();
            expect(updatedStats.totalConnections).toBe(1);
            expect(updatedStats.messagesSent).toBe(1);
            expect(updatedStats.uptime).toBeGreaterThan(0);
            
            client.destroy();
        });

        test('should track latency', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            // Simulate pong response
            client.socket._simulateLatency(25);
            
            expect(client.latency).toBe(25);
            expect(client.getStats().latency).toBe(25);
            
            client.destroy();
        });

        test('should provide connection state information', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            let state = client.getState();
            expect(state.connectionState).toBe('disconnected');
            expect(state.sessionId).toBeNull();
            
            await client.connect();
            
            state = client.getState();
            expect(state.connectionState).toBe('connected');
            expect(state.sessionId).toBe('mock-session-id');
            
            client.destroy();
        });
    });

    describe('Error Handling', () => {
        test('should handle Socket.IO unavailable', () => {
            // Remove io from global scope
            delete global.io;
            if (typeof window !== 'undefined') {
                delete window.io;
            }
            
            const client = new WebSocketClient({ autoConnect: false });
            
            expect(async () => {
                await client.connect();
            }).rejects.toThrow('Socket.IO library not available');
            
            client.destroy();
        });

        test('should handle error events', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            let errorReceived = null;
            client.onError((error) => {
                errorReceived = error;
            });
            
            await client.connect();
            
            // Simulate error
            const testError = new Error('Test error');
            client.socket._trigger('connect_error', testError);
            
            expect(errorReceived).toBeTruthy();
            expect(errorReceived.type).toBe('connection_error');
            expect(errorReceived.error).toBe(testError);
            
            client.destroy();
        });
    });

    describe('Cleanup and Destruction', () => {
        test('should clean up resources on destroy', async () => {
            const client = new WebSocketClient({ autoConnect: false });
            await client.connect();
            
            client.joinRoom('test_room');
            client.on('test_event', () => {});
            client.emit('test', {});
            
            expect(client.joinedRooms.size).toBeGreaterThan(0);
            expect(client.eventHandlers.size).toBeGreaterThan(0);
            
            client.destroy();
            
            expect(client.connectionState).toBe('disconnected');
            expect(client.joinedRooms.size).toBe(0);
            expect(client.eventHandlers.size).toBe(0);
            expect(client.messageQueue.length).toBe(0);
        });

        test('should disable and clear message queue', () => {
            const client = new WebSocketClient({ autoConnect: false });
            
            // Queue some messages
            client.emit('test1', {});
            client.emit('test2', {});
            expect(client.messageQueue.length).toBe(2);
            
            // Disable queuing
            client.setQueueEnabled(false);
            expect(client.messageQueue.length).toBe(0);
            
            // Try to queue more messages
            client.emit('test3', {});
            expect(client.messageQueue.length).toBe(0);
            
            client.destroy();
        });
    });
});

// Export test suite for Node.js environment
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        MockSocket,
        mockIo
    };
}