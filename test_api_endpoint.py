#!/usr/bin/env python3
"""
Script to test the marking guide API endpoint.
"""

import requests
import json

def test_api_endpoint():
    """Test the marking guide API endpoint."""
    guide_id = "dfdb0ccd-e777-43a0-8efc-ac5f030e135e"
    url = f"http://127.0.0.1:5000/api/marking-guides/{guide_id}"
    
    try:
        print(f"Testing API endpoint: {url}")
        response = requests.get(url)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Response JSON: {json.dumps(data, indent=2)}")
            except json.JSONDecodeError:
                print(f"Response Text: {response.text}")
        else:
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_api_endpoint()