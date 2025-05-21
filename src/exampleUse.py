"""
exampleUse.py: Example usage of EchonetLiteClient

This script demonstrates how to use the EchonetLiteClient to query the operation status of an ECHONET Lite device and print the response.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), './src')))
import enl_class as enl

#using enl_class write an example code to query the operation status of the device
# and print the response

if __name__ == "__main__":
    # Create an instance of the EchonetLiteClient
    client = enl.EchonetLiteClient('192.168.1.192')  # Replace with your device's IP address
    try:
        # Query the operation status
        response = client.get_operation_status()
        
        # Print the response
        print("Operation Status Response:", response)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the client connection
        client.close()