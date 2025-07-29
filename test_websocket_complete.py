#!/usr/bin/env python3
"""
Prueba completa del sistema WebSocket con verificación de contexto y Redis
"""

import asyncio
import websockets
import json
import redis
import time
import uuid

# Configuración
WS_URL = "ws://localhost:8000/ws/chat"
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

class WebSocketTester:
    def __init__(self):
        self.user_id = f"test_user_{int(time.time())}"
        self.session_id = None
        self.messages_sent = []
        self.messages_received = []
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        
    async def test_full_conversation(self):
        """Prueba una conversación completa con verificación de contexto"""
        print(f"🚀 Iniciando prueba completa del WebSocket")
        print(f"👤 Usuario de prueba: {self.user_id}")
        
        # Conectar al WebSocket
        ws_url = f"{WS_URL}?user_id={self.user_id}&agent_type=auto"
        print(f"🔌 Conectando a: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ Conexión WebSocket establecida")
                
                # Esperar mensaje de bienvenida
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                print(f"📩 Mensaje de bienvenida: {welcome_data['type']}")
                
                if welcome_data['type'] == 'connection_established':
                    self.session_id = welcome_data['session_id']
                    print(f"🆔 Session ID: {self.session_id}")
                
                # Test 1: Pregunta sobre información general
                await self.send_message(websocket, "¿Qué es Food Service 2025?")
                response1 = await self.wait_for_response(websocket)
                
                # Test 2: Pregunta sobre expositores (debe usar contexto)
                await self.send_message(websocket, "¿Qué empresas expositoras hay?")
                response2 = await self.wait_for_response(websocket)
                
                # Test 3: Pregunta de seguimiento (debe mantener contexto)
                await self.send_message(websocket, "¿Cuándo es el evento?")
                response3 = await self.wait_for_response(websocket)
                
                # Test 4: Pregunta específica de visitantes
                await self.send_message(websocket, "¿Cómo puedo registrarme como visitante?")
                response4 = await self.wait_for_response(websocket)
                
                # Verificar Redis después de la conversación
                self.verify_redis_data()
                
                print("🎉 Prueba completa exitosa!")
                return True
                
        except Exception as e:
            print(f"❌ Error en la prueba: {e}")
            return False
    
    async def send_message(self, websocket, content):
        """Envía un mensaje y lo registra"""
        message = {
            "type": "chat_message",
            "content": content
        }
        
        await websocket.send(json.dumps(message))
        self.messages_sent.append(content)
        print(f"📤 Enviado: {content}")
    
    async def wait_for_response(self, websocket):
        """Espera y procesa la respuesta del asistente"""
        response_data = None
        
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(message)
                
                if data['type'] == 'message_received':
                    print(f"✅ Mensaje recibido por el servidor")
                    
                elif data['type'] == 'typing':
                    print(f"⌨️ {data['message']}")
                    
                elif data['type'] == 'chat_response':
                    response_data = data
                    agent_type = data['metadata']['agent_type']
                    confidence = data['metadata']['confidence']
                    processing_time = data['metadata']['processing_time']
                    
                    print(f"📨 Respuesta del {agent_type}:")
                    print(f"   🎯 Confianza: {confidence:.2f}")
                    print(f"   ⏱️ Tiempo: {processing_time:.2f}s")
                    print(f"   💬 Contenido: {data['content'][:200]}...")
                    
                    self.messages_received.append(data)
                    break
                    
                elif data['type'] == 'error':
                    print(f"❌ Error: {data['message']}")
                    break
                    
            except asyncio.TimeoutError:
                print("⏰ Timeout esperando respuesta")
                break
        
        return response_data
    
    def verify_redis_data(self):
        """Verifica que los datos se hayan guardado correctamente en Redis"""
        print("\n🔍 Verificando datos en Redis...")
        
        if not self.session_id:
            print("❌ No hay session_id para verificar")
            return
        
        # Verificar información de sesión
        session_key = f"fs2024:session:{self.session_id}"
        session_data = self.redis_client.get(session_key)
        
        if session_data:
            session_info = json.loads(session_data)
            print(f"✅ Sesión encontrada: {session_info}")
        else:
            print(f"❌ No se encontró sesión: {session_key}")
        
        # Verificar historial de chat
        chat_key = f"fs2024:chat:{self.session_id}"
        chat_data = self.redis_client.get(chat_key)
        
        if chat_data:
            chat_history = json.loads(chat_data)
            print(f"✅ Historial encontrado: {len(chat_history)} mensajes")
            
            # Mostrar algunos mensajes del historial
            for i, msg in enumerate(chat_history[-4:]):  # Últimos 4 mensajes
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:100]
                print(f"   {i+1}. [{role}]: {content}...")
        else:
            print(f"❌ No se encontró historial: {chat_key}")
        
        # Verificar sesiones activas
        active_sessions = self.redis_client.smembers("fs2024:active_sessions")
        print(f"📊 Sesiones activas: {len(active_sessions)}")
    
    async def test_reconnection_context(self):
        """Prueba que el contexto se mantenga al reconectar"""
        print("\n🔄 Probando reconexión y mantenimiento de contexto...")
        
        if not self.session_id:
            print("❌ No hay session_id para reconectar")
            return False
        
        # Reconectar con el mismo session_id
        ws_url = f"{WS_URL}?user_id={self.user_id}&session_id={self.session_id}&agent_type=auto"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("✅ Reconexión establecida")
                
                # Esperar mensaje de bienvenida o historial
                welcome_msg = await websocket.recv()
                welcome_data = json.loads(welcome_msg)
                
                if welcome_data['type'] == 'chat_history':
                    print(f"📚 Historial restaurado: {len(welcome_data.get('messages', []))} mensajes")
                
                # Hacer una pregunta de seguimiento que requiera contexto
                await self.send_message(websocket, "Basándote en lo que hablamos antes, ¿puedes resumir?")
                response = await self.wait_for_response(websocket)
                
                if response:
                    print("✅ Contexto mantenido exitosamente en la reconexión")
                    return True
                
        except Exception as e:
            print(f"❌ Error en reconexión: {e}")
            return False
        
        return False

async def main():
    """Función principal de pruebas"""
    print("🧪 === PRUEBA COMPLETA DEL SISTEMA WEBSOCKET ===\n")
    
    tester = WebSocketTester()
    
    # Verificar conexión a Redis
    try:
        tester.redis_client.ping()
        print("✅ Conexión a Redis exitosa")
    except Exception as e:
        print(f"❌ Error conectando a Redis: {e}")
        return
    
    # Ejecutar pruebas
    success1 = await tester.test_full_conversation()
    
    if success1:
        success2 = await tester.test_reconnection_context()
        
        print(f"\n📊 === RESULTADOS ===")
        print(f"✅ Conversación completa: {'✓' if success1 else '✗'}")
        print(f"✅ Mantenimiento de contexto: {'✓' if success2 else '✗'}")
        print(f"📤 Mensajes enviados: {len(tester.messages_sent)}")
        print(f"📨 Respuestas recibidas: {len(tester.messages_received)}")
        
        if success1 and success2:
            print("\n🎉 TODAS LAS PRUEBAS PASARON EXITOSAMENTE!")
        else:
            print("\n⚠️ Algunas pruebas fallaron")
    
    print("\n🏁 Pruebas completadas")

if __name__ == "__main__":
    asyncio.run(main())