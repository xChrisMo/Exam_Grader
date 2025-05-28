#!/usr/bin/env python3
"""
Simple test Flask application to verify setup
"""

from flask import Flask, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-secret-key'

@app.route('/')
def test():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Exam Grader Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 600px; margin: 0 auto; text-align: center; }
            .success { color: #28a745; }
            .info { color: #007bff; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="success">✅ Flask Application Running!</h1>
            <p class="info">The Exam Grader web application is working correctly.</p>
            <p>You can now access the full application.</p>
            <hr>
            <p><strong>Next steps:</strong></p>
            <ul style="text-align: left;">
                <li>Install required dependencies: <code>pip install -r requirements.txt</code></li>
                <li>Run the main application: <code>python exam_grader_app.py</code></li>
                <li>Access the dashboard at: <a href="http://127.0.0.1:5000">http://127.0.0.1:5000</a></li>
            </ul>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("🧪 Starting Test Flask Application...")
    print("📊 Test page: http://127.0.0.1:5000")
    print("🔧 Debug mode: ON")
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=True
    )
