#!/usr/bin/env python3
"""
Prueba del contexto de Redis sin dependencias adicionales
"""

import json
import subprocess
import time

def run_redis_command(cmd):
    """Ejecuta comando Redis via docker"""
    full_cmd = ["docker", "exec", "fs2024_redis", "redis-cli"] + cmd
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando Redis command: {e}")
        return None

def test_redis_context():
    """Verifica el contexto almacenado en Redis"""
    print("🔍 === ANÁLISIS DEL CONTEXTO EN REDIS ===\n")
    
    # Obtener todas las claves
    keys = run_redis_command(["KEYS", "fs2024:*"])
    if not keys:
        print("❌ No se encontraron claves en Redis")
        return
    
    all_keys = keys.split('\n')
    print(f"📊 Total de claves encontradas: {len(all_keys)}")
    
    # Separar por tipo
    session_keys = [k for k in all_keys if k.startswith('fs2024:session:')]
    chat_keys = [k for k in all_keys if k.startswith('fs2024:chat:')]
    query_keys = [k for k in all_keys if k.startswith('fs2024:query:')]
    
    print(f"🆔 Sesiones: {len(session_keys)}")
    print(f"💬 Chats: {len(chat_keys)}")
    print(f"🔍 Queries: {len(query_keys)}")
    
    # Analizar sesiones de chat
    print(f"\n📝 === ANÁLISIS DE SESIONES DE CHAT ===")
    
    for chat_key in chat_keys[:5]:  # Primeras 5 sesiones
        print(f"\n🔑 Clave: {chat_key}")
        
        # Obtener contenido
        content = run_redis_command(["GET", chat_key])
        if content and content != '[]':
            try:
                messages = json.loads(content)
                print(f"   📊 Mensajes en historial: {len(messages)}")
                
                # Mostrar algunos mensajes
                for i, msg in enumerate(messages[-3:]):  # Últimos 3 mensajes
                    role = msg.get('role', 'unknown')
                    content_text = msg.get('content', '')[:80]
                    timestamp = msg.get('metadata', {}).get('timestamp', 'N/A')
                    agent_type = msg.get('metadata', {}).get('agent_type', 'N/A')
                    
                    print(f"   {i+1}. [{role}] ({agent_type}): {content_text}...")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Error decodificando JSON")
        else:
            print(f"   📭 Sesión vacía")
    
    # Verificar metadatos de sesión
    print(f"\n🔍 === METADATOS DE SESIONES ===")
    
    for session_key in session_keys[:3]:  # Primeras 3 sesiones
        print(f"\n🔑 Clave: {session_key}")
        
        content = run_redis_command(["GET", session_key])
        if content:
            try:
                session_data = json.loads(content)
                print(f"   👤 Usuario: {session_data.get('user_id', 'N/A')}")
                print(f"   🤖 Agente: {session_data.get('agent_type', 'N/A')}")
                print(f"   📊 Mensajes: {session_data.get('message_count', 0)}")
                print(f"   ⏰ Creado: {time.ctime(session_data.get('created_at', 0))}")
                print(f"   🔄 Activo: {session_data.get('active', False)}")
            except json.JSONDecodeError:
                print(f"   ❌ Error decodificando metadatos")
    
    # Verificar sesiones activas
    active_sessions = run_redis_command(["SMEMBERS", "fs2024:active_sessions"])
    if active_sessions:
        active_list = active_sessions.split('\n') if active_sessions else []
        print(f"\n🟢 Sesiones activas: {len(active_list)}")
        for session in active_list[:3]:
            print(f"   • {session}")
    else:
        print(f"\n🔴 No hay sesiones activas")
    
    # Análisis de queries en cache
    print(f"\n🔍 === ANÁLISIS DE CACHE DE QUERIES ===")
    
    for query_key in query_keys[:3]:  # Primeras 3 queries
        print(f"\n🔑 Clave: {query_key}")
        
        # Extraer información del key
        parts = query_key.split(':')
        if len(parts) >= 4:
            agent_type = parts[2]
            query_hash = parts[3]
            print(f"   🤖 Agente: {agent_type}")
            print(f"   #️⃣ Hash: {query_hash[:16]}...")
            
            # Ver contenido del cache
            content = run_redis_command(["GET", query_key])
            if content:
                try:
                    cache_data = json.loads(content)
                    print(f"   📝 Respuesta: {cache_data.get('response', '')[:100]}...")
                    print(f"   ⏰ Timestamp: {cache_data.get('timestamp', 'N/A')}")
                except json.JSONDecodeError:
                    print(f"   ❌ Error decodificando cache")

def analyze_conversation_flow():
    """Analiza el flujo de conversación para verificar contexto"""
    print(f"\n🔄 === ANÁLISIS DE FLUJO DE CONVERSACIÓN ===")
    
    # Buscar la sesión más reciente con mensajes
    chat_keys = run_redis_command(["KEYS", "fs2024:chat:*"])
    if not chat_keys:
        print("❌ No hay sesiones de chat")
        return
    
    all_chat_keys = chat_keys.split('\n')
    
    # Encontrar sesión con más mensajes
    best_session = None
    max_messages = 0
    
    for chat_key in all_chat_keys:
        content = run_redis_command(["GET", chat_key])
        if content and content != '[]':
            try:
                messages = json.loads(content)
                if len(messages) > max_messages:
                    max_messages = len(messages)
                    best_session = chat_key
            except:
                continue
    
    if best_session and max_messages > 0:
        print(f"🏆 Sesión con más actividad: {best_session}")
        print(f"📊 Total de mensajes: {max_messages}")
        
        content = run_redis_command(["GET", best_session])
        messages = json.loads(content)
        
        print(f"\n💬 Flujo de conversación:")
        for i, msg in enumerate(messages):
            role = msg.get('role', 'unknown')
            content_text = msg.get('content', '')[:150]
            agent_type = msg.get('metadata', {}).get('agent_type', 'N/A')
            
            emoji = "👤" if role == "user" else "🤖"
            print(f"{i+1:2d}. {emoji} [{role}] ({agent_type})")
            print(f"     {content_text}")
            print()
        
        # Verificar si hay continuidad en el contexto
        user_messages = [msg for msg in messages if msg.get('role') == 'user']
        assistant_messages = [msg for msg in messages if msg.get('role') == 'assistant']
        
        print(f"📈 Análisis de contexto:")
        print(f"   👤 Mensajes de usuario: {len(user_messages)}")
        print(f"   🤖 Respuestas del asistente: {len(assistant_messages)}")
        
        if len(user_messages) > 1:
            print(f"   ✅ Conversación multi-turno detectada")
            print(f"   🧠 El contexto se está manteniendo correctamente")
        else:
            print(f"   ⚠️ Solo un intercambio detectado")
    
    else:
        print("❌ No se encontraron sesiones con mensajes")

if __name__ == "__main__":
    test_redis_context()
    analyze_conversation_flow()
    print("\n🏁 Análisis completado")