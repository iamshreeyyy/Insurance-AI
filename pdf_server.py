#!/usr/bin/env python3
"""
Simple HTTP server to serve local PDF files for testing webhook with real Gemini processing
"""

import http.server
import socketserver
import os
import threading
import time

def start_pdf_server():
    """Start a simple HTTP server to serve PDF files"""
    os.chdir("/home/shrey/Downloads/Insurance-Agentic-AI/data")
    
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"🌐 PDF server running on http://localhost:{PORT}")
            print("📁 Serving files from: /home/shrey/Downloads/Insurance-Agentic-AI/data")
            print("📄 Available PDFs:")
            for file in os.listdir("."):
                if file.endswith(".pdf"):
                    print(f"   - http://localhost:{PORT}/{file}")
            print()
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("👋 PDF server stopped")

if __name__ == "__main__":
    start_pdf_server()
