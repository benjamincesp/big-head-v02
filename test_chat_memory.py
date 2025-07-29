"""
Test script for Chat Memory System
Tests the Redis-based chat memory functionality
"""

import asyncio
import json
import time
from cache.redis_manager import RedisManager
from cache.chat_memory_manager import ChatMemoryManager

async def test_chat_memory_system():
    """Test the complete chat memory system"""
    
    print("🧪 Testing Chat Memory System")
    print("=" * 50)
    
    # Initialize Redis and Chat Memory Manager
    print("1. Initializing Redis and Chat Memory Manager...")
    redis_manager = RedisManager()
    
    if not redis_manager.is_connected():
        print("❌ Redis not connected! Make sure Redis is running.")
        return
    
    chat_memory = ChatMemoryManager(redis_manager, default_ttl=3600)  # 1 hour for testing
    print("✅ Chat Memory Manager initialized")
    
    # Test 1: Create a new chat session
    print("\n2. Creating new chat session...")
    session_id = chat_memory.create_session(user_id="test_user_001", agent_type="general")
    
    if session_id:
        print(f"✅ Session created: {session_id}")
    else:
        print("❌ Failed to create session")
        return
    
    # Test 2: Add messages to the session
    print("\n3. Adding messages to the session...")
    
    # User message
    success = chat_memory.add_message(
        session_id=session_id,
        role="user",
        content="Hola, ¿qué información tienes sobre FOAMBOARD?",
        metadata={"source": "test", "timestamp": time.time()}
    )
    print(f"✅ User message added: {success}")
    
    # Assistant response
    success = chat_memory.add_message(
        session_id=session_id,
        role="assistant", 
        content="El FOAMBOARD SOBRE PANEL tiene un precio de US$175 + IVA, equivalente a 3.8 UF + IVA o US$154 + VAT. Es un material versátil para stands en Food Service 2025.",
        metadata={"agent_type": "general", "confidence": 0.9, "sources": ["catalog.pdf"]}
    )
    print(f"✅ Assistant message added: {success}")
    
    # Follow-up user message
    success = chat_memory.add_message(
        session_id=session_id,
        role="user",
        content="¿Cuáles son las medidas disponibles?",
        metadata={"source": "test", "timestamp": time.time()}
    )
    print(f"✅ Follow-up message added: {success}")
    
    # Test 3: Retrieve messages
    print("\n4. Retrieving messages...")
    messages = chat_memory.get_messages(session_id)
    print(f"✅ Retrieved {len(messages)} messages:")
    
    for i, msg in enumerate(messages, 1):
        print(f"   {i}. [{msg['role']}] {msg['content'][:50]}...")
    
    # Test 4: Get OpenAI format messages
    print("\n5. Getting OpenAI format messages...")
    openai_messages = chat_memory.get_openai_format_messages(session_id)
    print(f"✅ OpenAI format messages ({len(openai_messages)}):")
    
    for msg in openai_messages:
        print(f"   - {msg['role']}: {msg['content'][:50]}...")
    
    # Test 5: Session information
    print("\n6. Getting session information...")
    session_info = chat_memory.get_session_info(session_id)
    print(f"✅ Session info:")
    print(f"   - User: {session_info['user_id']}")
    print(f"   - Agent: {session_info['agent_type']}")
    print(f"   - Messages: {session_info['message_count']}")
    print(f"   - Active: {session_info['active']}")
    
    # Test 6: Create another session to test multiple sessions
    print("\n7. Creating second session...")
    session_id_2 = chat_memory.create_session(user_id="test_user_002", agent_type="exhibitors")
    
    chat_memory.add_message(
        session_id=session_id_2,
        role="user",
        content="¿Cuántas empresas participan en Food Service 2025?",
        metadata={"source": "test"}
    )
    
    print(f"✅ Second session created: {session_id_2}")
    
    # Test 7: Get system statistics
    print("\n8. Getting system statistics...")
    stats = chat_memory.get_chat_stats()
    print(f"✅ Chat system stats:")
    print(f"   - Active sessions: {stats['active_sessions']}")
    print(f"   - Total messages: {stats['total_messages']}")
    print(f"   - Agent stats: {stats['agent_type_stats']}")
    
    # Test 8: Test session persistence (simulate reconnection)
    print("\n9. Testing session persistence...")
    
    # Create new ChatMemoryManager (simulating restart)
    new_chat_memory = ChatMemoryManager(redis_manager, default_ttl=3600)
    
    # Retrieve messages from first session
    persistent_messages = new_chat_memory.get_messages(session_id)
    print(f"✅ Retrieved {len(persistent_messages)} messages after 'restart'")
    
    # Test 9: Close sessions
    print("\n10. Closing sessions...")
    success_1 = chat_memory.close_session(session_id)
    success_2 = chat_memory.close_session(session_id_2)
    print(f"✅ Sessions closed: {success_1} and {success_2}")
    
    # Test 10: Cleanup test
    print("\n11. Testing cleanup...")
    cleaned = chat_memory.cleanup_expired_sessions()
    print(f"✅ Cleaned up {cleaned} expired sessions")
    
    print("\n" + "=" * 50)
    print("🎉 Chat Memory System test completed successfully!")

async def test_websocket_integration():
    """Test WebSocket integration preparation"""
    
    print("\n🔌 Testing WebSocket Integration Preparation")
    print("=" * 50)
    
    # Test Redis connection for WebSocket use
    redis_manager = RedisManager()
    
    if not redis_manager.is_connected():
        print("❌ Redis not connected for WebSocket test")
        return
    
    chat_memory = ChatMemoryManager(redis_manager)
    
    # Simulate WebSocket session creation
    print("1. Simulating WebSocket session creation...")
    session_id = chat_memory.create_session(user_id="websocket_user", agent_type="general")
    print(f"✅ WebSocket session: {session_id}")
    
    # Simulate real-time message exchange
    print("\n2. Simulating real-time message exchange...")
    
    # User connects and sends first message
    chat_memory.add_message(session_id, "user", "Hola, conectado via WebSocket")
    
    # Get conversation history for OpenAI context
    history = chat_memory.get_openai_format_messages(session_id)
    print(f"✅ Context for OpenAI: {len(history)} messages")
    
    # Simulate assistant response with context
    chat_memory.add_message(
        session_id, 
        "assistant", 
        "¡Hola! Veo que te has conectado exitosamente. ¿En qué puedo ayudarte con Food Service 2025?",
        metadata={"websocket": True, "context_used": True}
    )
    
    # User follow-up (context-aware)
    chat_memory.add_message(session_id, "user", "Cuéntame sobre los expositores")
    
    # Get updated context
    updated_history = chat_memory.get_openai_format_messages(session_id)
    print(f"✅ Updated context: {len(updated_history)} messages")
    
    print("\n3. Messages in conversation:")
    for msg in updated_history:
        print(f"   - {msg['role']}: {msg['content']}")
    
    # Test session resumption
    print("\n4. Testing session resumption...")
    messages_before = len(chat_memory.get_messages(session_id))
    
    # Simulate disconnection and reconnection
    # Add message after "reconnection"
    chat_memory.add_message(session_id, "user", "Me reconecté, ¿recuerdas de qué estábamos hablando?")
    
    messages_after = len(chat_memory.get_messages(session_id))
    print(f"✅ Session resumed: {messages_before} -> {messages_after} messages")
    
    # Clean up
    chat_memory.close_session(session_id)
    print("✅ WebSocket simulation completed")

if __name__ == "__main__":
    print("🚀 Starting Chat Memory System Tests")
    
    # Run the main test
    asyncio.run(test_chat_memory_system())
    
    # Run WebSocket integration test
    asyncio.run(test_websocket_integration())
    
    print("\n✅ All tests completed!")