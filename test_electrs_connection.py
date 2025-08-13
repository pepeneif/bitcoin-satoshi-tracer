#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick test script to validate Electrs connection and functionality.
Run this before starting the full application to ensure everything works.
"""
import sys
import os
import logging

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_electrs_integration():
    """Test the complete Electrs integration"""
    try:
        print("🔧 Testing Electrs Integration...")
        print("=" * 50)
        
        # Test 1: Import modules
        print("📦 Testing module imports...")
        try:
            from electrs_client import test_electrs_connection, validate_txid
            print("✅ Successfully imported electrum_client module")
        except ImportError as e:
            print(f"❌ Failed to import modules: {e}")
            print("💡 Make sure to install dependencies: pip install -r backend/requirements.txt")
            return False
        
        # Test 2: Environment configuration
        print("\n🔐 Testing environment configuration...")
        electrs_host = os.getenv('ELECTRS_HOST', '127.0.0.1')
        electrs_port = os.getenv('ELECTRS_PORT', '50001')
        electrs_use_ssl = os.getenv('ELECTRS_USE_SSL', 'false')
        
        print(f"   ELECTRS_HOST: {electrs_host}")
        print(f"   ELECTRS_PORT: {electrs_port}")
        print(f"   ELECTRS_USE_SSL: {electrs_use_ssl}")
        
        if electrs_host == '127.0.0.1':
            print("⚠️  Using default localhost. Update ELECTRS_HOST in .env for remote servers.")
        
        # Test 3: Connection test
        print("\n🌐 Testing Electrs server connection...")
        connection_result = test_electrs_connection()
        
        if connection_result['connected']:
            print(f"✅ Connection successful: {connection_result['message']}")
        else:
            print(f"❌ Connection failed: {connection_result['message']}")
            print("\n🔧 Troubleshooting tips:")
            print("   1. Check that your Electrs server is running")
            print("   2. Verify ELECTRS_HOST and ELECTRS_PORT in .env")
            print("   3. Ensure firewall allows connections to the Electrs port")
            print("   4. For Umbrel: use your node's local IP address")
            return False
        
        # Test 4: TXID validation
        print("\n🔍 Testing transaction validation...")
        test_txid = "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
        if validate_txid(test_txid):
            print("✅ TXID validation working correctly")
        else:
            print("❌ TXID validation failed")
            return False
        
        print("\n🎉 All tests passed! The Electrs integration is ready.")
        print("\n📋 Next steps:")
        print("   1. Update your .env file with correct Electrs server details")
        print("   2. Run: docker-compose up --build")
        print("   3. Open http://localhost:3000")
        print("   4. Test with a real Bitcoin transaction ID")
        
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error during testing: {e}")
        return False

if __name__ == '__main__':
    # Load environment from .env file if it exists
    env_path = '.env'
    if os.path.exists(env_path):
        print(f"📄 Loading environment from {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value
    else:
        print("⚠️  No .env file found. Using default values.")
        print("💡 Copy .env.example to .env and configure your Electrs server")
    
    success = test_electrs_integration()
    sys.exit(0 if success else 1)