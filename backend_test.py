import requests
import json
import time
import random
import string
from datetime import datetime

class CashlessSystemTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.test_user_email = f"test_user_{int(time.time())}@test.com"
        self.test_user_password = "Test@123"
        self.test_user_name = f"Test User {int(time.time())}"
        self.tests_run = 0
        self.tests_passed = 0
        self.recipient_id = None
        self.recipient_name = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)

            print(f"Status: {response.status_code}")
            
            if response.status_code == expected_status:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health check endpoint"""
        return self.run_test(
            "Health Check",
            "GET",
            "/api/health",
            200
        )

    def test_register(self):
        """Test user registration"""
        success, response = self.run_test(
            "User Registration",
            "POST",
            "/api/register",
            200,
            data={
                "email": self.test_user_email,
                "name": self.test_user_name,
                "password": self.test_user_password
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            print(f"User created with ID: {self.user_id}")
            return True
        return False

    def test_login(self):
        """Test user login"""
        success, response = self.run_test(
            "User Login",
            "POST",
            "/api/login",
            200,
            data={
                "email": self.test_user_email,
                "password": self.test_user_password
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_id = response['user']['id']
            print(f"User logged in with ID: {self.user_id}")
            return True
        return False

    def test_profile(self):
        """Test getting user profile"""
        success, response = self.run_test(
            "Get User Profile",
            "GET",
            "/api/profile",
            200
        )
        return success

    def test_recharge(self, amount=100.0):
        """Test recharging wallet"""
        success, response = self.run_test(
            "Recharge Wallet",
            "POST",
            "/api/recharge",
            200,
            data={"amount": amount}
        )
        
        if success:
            print(f"New balance: {response.get('new_balance', 'N/A')}")
        return success

    def test_generate_qr(self):
        """Test QR code generation"""
        success, response = self.run_test(
            "Generate QR Code",
            "GET",
            "/api/generate-qr",
            200
        )
        
        if success:
            print(f"QR data: {response.get('qr_data', 'N/A')}")
            if 'qr_image' in response:
                print("QR image generated successfully")
        return success

    def test_search_users(self, query):
        """Test user search"""
        success, response = self.run_test(
            "Search Users",
            "GET",
            f"/api/users/search?q={query}",
            200
        )
        
        if success and len(response) > 0:
            self.recipient_id = response[0]['id']
            self.recipient_name = response[0]['name']
            print(f"Found user: {self.recipient_name} (ID: {self.recipient_id})")
        return success

    def test_payment(self, amount=10.0, method="transfer"):
        """Test making a payment"""
        if not self.recipient_id:
            print("❌ No recipient found for payment test")
            return False
            
        success, response = self.run_test(
            f"Make Payment ({method})",
            "POST",
            "/api/pay",
            200,
            data={
                "to_user": self.recipient_id,
                "amount": amount,
                "description": f"Test payment via {method}",
                "method": method
            }
        )
        
        if success:
            print(f"Payment successful. New balance: {response.get('new_balance', 'N/A')}")
        return success

    def test_transactions(self):
        """Test getting transaction history"""
        success, response = self.run_test(
            "Get Transactions",
            "GET",
            "/api/transactions",
            200
        )
        
        if success:
            print(f"Found {len(response)} transactions")
        return success

    def create_second_user(self):
        """Create a second user for payment testing"""
        second_email = f"recipient_{int(time.time())}@test.com"
        second_password = "Test@123"
        second_name = f"Recipient User {int(time.time())}"
        
        success, response = self.run_test(
            "Create Second User",
            "POST",
            "/api/register",
            200,
            data={
                "email": second_email,
                "name": second_name,
                "password": second_password
            }
        )
        
        if success and 'user' in response:
            self.recipient_id = response['user']['id']
            self.recipient_name = response['user']['name']
            print(f"Created recipient: {self.recipient_name} (ID: {self.recipient_id})")
            # Restore original user's token
            self.test_login()
            return True
        return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Cashless System API Tests")
        print(f"API URL: {self.base_url}")
        print("=" * 50)
        
        # Basic health check
        self.test_health_check()
        
        # Authentication tests
        if not self.test_register():
            print("❌ Registration failed, stopping tests")
            return self.report_results()
            
        if not self.test_profile():
            print("❌ Profile retrieval failed, stopping tests")
            return self.report_results()
            
        # Create a second user for payment testing
        self.create_second_user()
        
        # Wallet tests
        self.test_recharge(100.0)
        
        # QR code tests
        self.test_generate_qr()
        
        # User search tests
        if self.recipient_id is None:
            self.test_search_users(self.recipient_name[:3])
        
        # Payment tests
        if self.recipient_id:
            self.test_payment(10.0, "transfer")
            self.test_payment(5.0, "qr")
        
        # Transaction history tests
        self.test_transactions()
        
        # Test login again
        self.token = None
        self.test_login()
        
        return self.report_results()
        
    def report_results(self):
        """Report test results"""
        print("\n" + "=" * 50)
        print(f"📊 Tests completed: {self.tests_run}")
        print(f"✅ Tests passed: {self.tests_passed}")
        print(f"❌ Tests failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success rate: {(self.tests_passed / self.tests_run) * 100:.2f}%")
        print("=" * 50)
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    # Get the backend URL from the frontend .env file
    API_URL = "https://00563b6e-dfeb-48d5-bb1d-5036f19ce413.preview.emergentagent.com"
    
    tester = CashlessSystemTester(API_URL)
    success = tester.run_all_tests()
    
    exit(0 if success else 1)