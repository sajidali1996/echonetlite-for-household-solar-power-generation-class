#using enl_class write an example code to query the operation status of the device
# and print the response
import enl_class as enl

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