from setuptools import setup, find_packages

setup(
    name="sync-with-playwright",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "dropbox",
        "python-dotenv",
        "playwright",
        "pandas",
        "PyPDF2",
        "pdf2image",
        "pytesseract",
        "opencv-python",
        "numpy",
        "Pillow"
    ],
    python_requires=">=3.7",
) 