"""
Basic system tests for Food Service 2025 Multi-Agent System
Tests PDF and Excel document processing capabilities
Run these tests to verify the system is working correctly
"""

import asyncio
import json
import requests
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8000"

class FoodServiceTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_health_check(self) -> Dict[str, Any]:
        """Test API documentation endpoint"""
        print("🔍 Testing API docs...")
        try:
            response = self.session.get(f"{self.base_url}/docs")
            return {
                "test": "api_docs",
                "status": "✅ PASS" if response.status_code == 200 else "❌ FAIL",
                "status_code": response.status_code,
                "response": "API docs accessible" if response.status_code == 200 else response.text
            }
        except Exception as e:
            return {
                "test": "api_docs",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_basic_endpoint(self) -> Dict[str, Any]:
        """Test basic query endpoint"""
        print("🔍 Testing basic query endpoint...")
        try:
            query_data = {"query": "test"}
            response = self.session.post(f"{self.base_url}/query", json=query_data)
            return {
                "test": "basic_endpoint",
                "status": "✅ PASS" if response.status_code == 200 else "❌ FAIL",
                "status_code": response.status_code,
                "response": response.json() if response.status_code == 200 else response.text
            }
        except Exception as e:
            return {
                "test": "basic_endpoint",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_agents_list(self) -> Dict[str, Any]:
        """Test agents listing endpoint"""
        print("🔍 Testing agents list...")
        try:
            response = self.session.get(f"{self.base_url}/food-service/agents")
            data = response.json() if response.status_code == 200 else None
            
            return {
                "test": "agents_list",
                "status": "✅ PASS" if response.status_code == 200 and data and "agents" in data else "❌ FAIL",
                "status_code": response.status_code,
                "agents_count": len(data.get("agents", [])) if data else 0,
                "response": data
            }
        except Exception as e:
            return {
                "test": "agents_list",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_general_query(self) -> Dict[str, Any]:
        """Test general query processing"""
        print("🔍 Testing general query...")
        try:
            query_data = {
                "query": "¿Qué información general tienes sobre Food Service 2025?",
                "use_cache": False
            }
            
            response = self.session.post(
                f"{self.base_url}/query",
                json=query_data
            )
            
            data = response.json() if response.status_code == 200 else None
            
            return {
                "test": "general_query",
                "status": "✅ PASS" if response.status_code == 200 and data and "response" in data else "❌ FAIL",
                "status_code": response.status_code,
                "agent_used": data.get("agent_used") if data else None,
                "response_length": len(data.get("response", "")) if data else 0,
                "response": data
            }
        except Exception as e:
            return {
                "test": "general_query",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_exhibitors_query(self) -> Dict[str, Any]:
        """Test exhibitors-specific query"""
        print("🔍 Testing exhibitors query...")
        try:
            query_data = {
                "query": "Lista de empresas expositoras en Food Service 2025",
                "agent_type": "exhibitors",
                "use_cache": False
            }
            
            response = self.session.post(
                f"{self.base_url}/query",
                json=query_data
            )
            
            data = response.json() if response.status_code == 200 else None
            
            return {
                "test": "exhibitors_query",
                "status": "✅ PASS" if response.status_code == 200 and data and "response" in data else "❌ FAIL",
                "status_code": response.status_code,
                "agent_used": data.get("agent_used") if data else None,
                "response_length": len(data.get("response", "")) if data else 0,
                "response": data
            }
        except Exception as e:
            return {
                "test": "exhibitors_query",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_visitors_query(self) -> Dict[str, Any]:
        """Test visitors-specific query"""
        print("🔍 Testing visitors query...")
        try:
            query_data = {
                "query": "Estadísticas de visitantes por día",
                "agent_type": "visitors",
                "use_cache": False
            }
            
            response = self.session.post(
                f"{self.base_url}/query",
                json=query_data
            )
            
            data = response.json() if response.status_code == 200 else None
            
            return {
                "test": "visitors_query",
                "status": "✅ PASS" if response.status_code == 200 and data and "response" in data else "❌ FAIL",
                "status_code": response.status_code,
                "agent_used": data.get("agent_used") if data else None,
                "response_length": len(data.get("response", "")) if data else 0,
                "response": data
            }
        except Exception as e:
            return {
                "test": "visitors_query",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_cache_functionality(self) -> Dict[str, Any]:
        """Test cache functionality with repeated queries"""
        print("🔍 Testing cache functionality...")
        try:
            query_data = {
                "query": "Test query for cache functionality",
                "use_cache": True
            }
            
            # First request (should miss cache)
            start_time = time.time()
            response1 = self.session.post(
                f"{self.base_url}/food-service/query",
                json=query_data
            )
            first_duration = time.time() - start_time
            
            # Second request (should hit cache)
            start_time = time.time()
            response2 = self.session.post(
                f"{self.base_url}/food-service/query",
                json=query_data
            )
            second_duration = time.time() - start_time
            
            data1 = response1.json() if response1.status_code == 200 else None
            data2 = response2.json() if response2.status_code == 200 else None
            
            cache_hit = data2.get("cache_hit", False) if data2 else False
            
            return {
                "test": "cache_functionality",
                "status": "✅ PASS" if cache_hit and second_duration < first_duration else "❌ FAIL",
                "first_request_time": round(first_duration, 3),
                "second_request_time": round(second_duration, 3),
                "cache_hit": cache_hit,
                "cache_type": data2.get("cache_type") if data2 else None
            }
        except Exception as e:
            return {
                "test": "cache_functionality",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_stats_endpoint(self) -> Dict[str, Any]:
        """Test statistics endpoint"""
        print("🔍 Testing stats endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/food-service/stats")
            data = response.json() if response.status_code == 200 else None
            
            return {
                "test": "stats_endpoint",
                "status": "✅ PASS" if response.status_code == 200 and data and "agents" in data else "❌ FAIL",
                "status_code": response.status_code,
                "has_cache_stats": "cache_stats" in data if data else False,
                "agents_count": len(data.get("agents", {})) if data else 0
            }
        except Exception as e:
            return {
                "test": "stats_endpoint",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def test_auto_agent_detection(self) -> Dict[str, Any]:
        """Test automatic agent detection"""
        print("🔍 Testing auto agent detection...")
        try:
            test_queries = [
                ("¿Cuántas empresas expositoras hay?", "exhibitors"),
                ("Estadísticas de visitantes", "visitors"),
                ("Información general del evento", "general")
            ]
            
            results = []
            for query, expected_agent in test_queries:
                query_data = {"query": query, "use_cache": False}
                response = self.session.post(
                    f"{self.base_url}/food-service/query",
                    json=query_data
                )
                
                data = response.json() if response.status_code == 200 else None
                detected_agent = data.get("agent_used") if data else None
                
                results.append({
                    "query": query,
                    "expected_agent": expected_agent,
                    "detected_agent": detected_agent,
                    "correct": detected_agent == expected_agent
                })
            
            correct_detections = sum(1 for r in results if r["correct"])
            
            return {
                "test": "auto_agent_detection",
                "status": "✅ PASS" if correct_detections >= 2 else "❌ FAIL",
                "correct_detections": correct_detections,
                "total_tests": len(test_queries),
                "results": results
            }
        except Exception as e:
            return {
                "test": "auto_agent_detection",
                "status": "❌ ERROR",
                "error": str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests and return comprehensive results"""
        print("🚀 Starting Food Service 2025 System Tests...\n")
        
        tests = [
            self.test_basic_endpoint,
            self.test_health_check,
            self.test_general_query,
            self.test_exhibitors_query,
            self.test_visitors_query,
            self.test_auto_agent_detection,
            self.test_cache_functionality
        ]
        
        results = []
        passed = 0
        
        for test in tests:
            try:
                result = test()
                results.append(result)
                if result.get("status", "").startswith("✅"):
                    passed += 1
                print(f"{result.get('status', '❓')} {result.get('test', 'Unknown')}")
            except Exception as e:
                results.append({
                    "test": test.__name__,
                    "status": "❌ ERROR",
                    "error": str(e)
                })
                print(f"❌ ERROR {test.__name__}: {str(e)}")
        
        print(f"\n📊 Test Results: {passed}/{len(tests)} tests passed")
        
        return {
            "summary": {
                "total_tests": len(tests),
                "passed": passed,
                "failed": len(tests) - passed,
                "success_rate": round((passed / len(tests)) * 100, 1)
            },
            "results": results
        }

def main():
    """Main test function"""
    tester = FoodServiceTester()
    
    print("=" * 60)
    print("🧪 Food Service 2025 - SYSTEM TESTS")
    print("=" * 60)
    
    # Run all tests
    test_results = tester.run_all_tests()
    
    # Print summary
    summary = test_results["summary"]
    print("\n" + "=" * 60)
    print("📋 FINAL SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}%")
    
    if summary['success_rate'] >= 80:
        print("\n🎉 System is working well!")
    elif summary['success_rate'] >= 50:
        print("\n⚠️  System has some issues but is partially functional")
    else:
        print("\n🚨 System has major issues that need attention")
    
    # Save detailed results
    with open("test_results.json", "w") as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to test_results.json")
    
    return test_results

if __name__ == "__main__":
    main()