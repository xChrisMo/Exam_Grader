# Exam Grader Web Application

A modern, responsive Flask web application for automated exam grading using AI-powered analysis.

## Features

- **Modern UI/UX**: Built with Tailwind CSS and responsive design
- **File Upload**: Drag-and-drop support for marking guides and submissions
- **AI Processing**: Automated grading with detailed feedback
- **Real-time Updates**: Progress tracking and status updates
- **Results Management**: Comprehensive grading results and export functionality
- **Mobile Responsive**: Works seamlessly on all devices

## Technology Stack

- **Backend**: Flask (Python)
- **Frontend**: HTML5, Tailwind CSS, Vanilla JavaScript
- **Styling**: Tailwind CSS with custom components
- **Icons**: Heroicons (SVG)
- **Fonts**: Inter (Google Fonts)

## Project Structure

```
webapp/
├── exam_grader_app.py      # Main Flask application
├── README.md              # This file
├── static/                # Static assets
│   ├── css/               # Stylesheets
│   ├── js/                # JavaScript files
│   └── favicon.ico        # Site icon
└── templates/             # Jinja2 templates
    ├── layout.html        # Base template
    ├── dashboard.html     # Main dashboard
    ├── upload_guide.html  # Guide upload page
    ├── upload_submission.html # Submission upload page
    ├── submissions.html   # Submissions list
    ├── results.html       # Grading results
    ├── marking_guides.html # Marking guides library
    ├── settings.html      # Application settings
    └── error.html         # Error pages
```

## Installation

1. **Navigate to the webapp directory**:
   ```bash
   cd webapp
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Development Mode

1. **Using the main run script** (recommended):
   ```bash
   cd ..
   python run_app.py
   ```

2. **Direct Flask execution**:
   ```bash
   python exam_grader_app.py
   ```

3. **Using Flask CLI**:
   ```bash
   export FLASK_APP=exam_grader_app.py  # On Windows: set FLASK_APP=exam_grader_app.py
   export FLASK_ENV=development         # On Windows: set FLASK_ENV=development
   flask run
   ```

The application will be available at: http://127.0.0.1:5000

### Production Mode

For production deployment, use a WSGI server like Gunicorn:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 exam_grader_app:app
```

## Usage

1. **Access the Dashboard**: Navigate to the home page to see the main dashboard
2. **Upload Marking Guide**: Upload your marking guide (PDF, Word, or image files)
3. **Upload Submissions**: Upload student submissions for grading
4. **Process Mapping**: Map student answers to marking guide questions
5. **Process Grading**: Run AI-powered grading analysis
6. **View Results**: Review detailed grading results and feedback

## Features Overview

### Dashboard
- System status monitoring
- Quick action cards
- Recent activity feed
- Statistics overview

### File Upload
- Drag-and-drop interface
- File validation
- Progress tracking
- Multiple format support (PDF, DOCX, images)

### Processing
- Answer mapping between submissions and guides
- AI-powered grading analysis
- Real-time progress updates
- Error handling and recovery

### Results
- Detailed question-by-question breakdown
- Overall scoring and feedback
- Export functionality
- Performance analytics

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Development

### Adding New Features

1. **Backend Routes**: Add new routes in `exam_grader_app.py`
2. **Templates**: Create new templates in `templates/`
3. **Styles**: Add custom CSS in `static/css/custom.css`
4. **JavaScript**: Add functionality in `static/js/app.js`

### Customization

- **Colors**: Modify the Tailwind color palette in `layout.html`
- **Fonts**: Change font families in the Tailwind config
- **Layout**: Adjust the responsive grid and layout components
- **Components**: Add new UI components following the existing patterns

## API Endpoints

- `GET /` - Dashboard
- `GET|POST /upload-guide` - Upload marking guide
- `GET|POST /upload-submission` - Upload submission
- `GET /submissions` - View submissions list
- `GET /results` - View grading results
- `POST /api/process-mapping` - Process answer mapping
- `POST /api/process-grading` - Process grading

## Configuration

The application uses fallback configuration when the main config system is not available:

- **Host**: 127.0.0.1
- **Port**: 5000
- **Debug**: True (development)
- **Max File Size**: 16MB
- **Supported Formats**: PDF, DOCX, DOC, JPG, JPEG, PNG, TIFF, BMP, GIF

## Security Features

- File type validation
- File size limits
- CSRF protection (Flask-WTF when available)
- Secure file handling
- Input sanitization

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're in the correct directory and virtual environment
2. **Port Already in Use**: Change the port in `run.py` or kill the existing process
3. **File Upload Issues**: Check file size and format restrictions
4. **Template Not Found**: Verify template files are in the `templates/` directory

### Debug Mode

The application runs in debug mode by default, providing:
- Detailed error messages
- Automatic reloading on code changes
- Interactive debugger in the browser

## Contributing

1. Follow the existing code style and patterns
2. Test your changes thoroughly
3. Update documentation as needed
4. Ensure responsive design compatibility

## License

This project is part of the Exam Grader system. See the main project documentation for license information.
