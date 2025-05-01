from setuptools import setup, find_packages

setup(
    name="exam_grader",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "streamlit==1.32.0",
        "requests==2.31.0",
        "python-dotenv==1.0.1",
        "PyMuPDF==1.23.8",
        "python-docx==1.1.0",
        "reportlab==4.1.0",
        "pytesseract==0.3.10",
        "Pillow==10.2.0",
        "python-magic==0.4.27",
        "python-magic-bin==0.4.14; sys_platform == 'win32'"
    ],
    python_requires=">=3.8",
    author="Exam Grader Team",
    description="A tool for parsing and grading exam submissions",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
) 