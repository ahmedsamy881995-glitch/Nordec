#!/bin/bash
echo "Installing requirements..."
pip install -r requirements.txt
echo ""
echo "Starting Nordec LIMS..."
streamlit run app.py
