#!/bin/bash
# Script to set Heroku environment variables
# Run this after deploying to Heroku
echo "Setting Heroku environment variables..."
# Set OpenAI API Key (replace with your actual key)
heroku config:set OPENAI_API_KEY=your_openai_api_key_here --app big-head-eaba7dc1431e
# Set Flask secret key
heroku config:set FLASK_SECRET_KEY=your_flask_secret_key_here --app big-head-eaba7dc1431e
# Set Python version
heroku config:set PYTHON_VERSION=3.11.0 --app big-head-eaba7dc1431e
echo "Environment variables set. Check with:"
echo "heroku config --app big-head-eaba7dc1431e"