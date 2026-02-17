from auto_uploader import BubloxUploader
import time

def test_uploader():
    print("Testing BubloxUploader...")
    uploader = BubloxUploader(headless=False) # Headless=False to see what happens
    
    try:
        uploader.start()
        
        # Test Login
        print("Testing Login...")
        uploader.login("kevintorresloyola@gmail.com", "Kkdvk123")
        
        # Test Get Categories
        categories = uploader.get_categories()
        print(f"Categories found: {categories}")
        
        if "Blox fruits" in categories:
            print("Category 'Blox fruits' found. Proceeding to upload.")
            # Test Upload with dummy data
            print("Testing Upload...")
            uploader.upload_script(
                title="Test Script - Blox Fruits Auto Farm",
                code="-- This is a test script\nprint('Hello World')",
                category="Blox fruits"
            )
        else:
            print("Category 'Blox fruits' NOT found. Skipping upload test.")
        
        print("Test Complete. Waiting 10s before closing...")
        time.sleep(10)
        
    except Exception as e:
        print(f"Test Failed: {e}")
    finally:
        uploader.close()

if __name__ == "__main__":
    test_uploader()
