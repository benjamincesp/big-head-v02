"""
Food Service 2025 Multi-Agent Orchestrator
Main orchestrator for routing queries to appropriate agents
"""

import logging
import os
from typing import Dict, Any, Optional
from agents import GeneralAgent, ExhibitorsAgent, VisitorsAgent
from cache import RedisManager, QueryCache

logger = logging.getLogger(__name__)

class FoodServiceOrchestrator:
    def __init__(self, openai_api_key: str, redis_config: Dict[str, Any] = None):
        """
        Initialize the multi-agent orchestrator
        
        Args:
            openai_api_key: OpenAI API key
            redis_config: Redis configuration parameters
        """
        print("🔧 DEBUG: Initializing orchestrator...")
        self.openai_api_key = openai_api_key
        
        # Initialize Redis and cache
        print("🔧 DEBUG: Setting up Redis connection...")
        redis_config = redis_config or {}
        self.redis_manager = RedisManager(**redis_config)
        self.query_cache = QueryCache(self.redis_manager)
        print("✅ DEBUG: Redis and cache initialized")
        
        # Initialize agents
        print("🔧 DEBUG: Creating agents...")
        print("🔧 DEBUG: Creating GeneralAgent...")
        self.agents = {
            'general': GeneralAgent(openai_api_key),
        }
        print("✅ DEBUG: GeneralAgent created")
        
        print("🔧 DEBUG: Creating ExhibitorsAgent...")
        self.agents['exhibitors'] = ExhibitorsAgent(openai_api_key)
        print("✅ DEBUG: ExhibitorsAgent created")
        
        print("🔧 DEBUG: Creating VisitorsAgent...")
        self.agents['visitors'] = VisitorsAgent(openai_api_key)
        print("✅ DEBUG: VisitorsAgent created")
        
        print("✅ DEBUG: All agents initialized!")
        
        # Try to restore cache from backup if Redis is empty
        print("🔄 DEBUG: Checking cache backup...")
        if self.query_cache.get_cache_stats().get("total_entries", 0) == 0:
            if self.query_cache.restore_cache_from_file():
                print("✅ DEBUG: Cache restored from backup")
            else:
                print("ℹ️ DEBUG: No cache backup to restore")
        else:
            print("ℹ️ DEBUG: Cache already populated, skipping backup restore")
        
        # Agent detection keywords
        self.agent_keywords = {
            'exhibitors': [
                'lista de expositores', 'nombres de empresas', 'cuántas empresas',
                'stands asignados', 'números de stand', 'empresas participantes',
                'directorio expositores', 'catálogo empresas'
            ],
            'visitors': [
                'cuántos visitantes', 'número de asistentes', 'estadísticas de público',
                'demografía visitantes', 'asistencia por día', 'cantidad de público',
                'datos de visitantes', 'cifras de asistencia'
            ]
        }
        
        # Narrative questions should go to general agent
        self.narrative_keywords = [
            'cómo', 'como', 'qué es', 'que es', 'donde', 'dónde', 'cuándo', 'cuando',
            'para qué', 'por qué', 'porque', 'asesoría', 'apoyo', 'servicio',
            'participar', 'inscribir', 'registrar', 'información sobre'
        ]
        
        logger.info("Food Service 2025 Orchestrator initialized")
    
    def detect_agent_type(self, query: str) -> str:
        """
        Detect which agent should handle the query based on keywords
        
        Args:
            query: User query
            
        Returns:
            Agent type ('general', 'exhibitors', or 'visitors')
        """
        query_lower = query.lower()
        
        # Check if it's a narrative question first
        for narrative_keyword in self.narrative_keywords:
            if narrative_keyword in query_lower:
                logger.info(f"Detected narrative question, using general agent")
                return 'general'
        
        # Count matches for specialized agents (only for data extraction queries)
        agent_scores = {'exhibitors': 0, 'visitors': 0}
        
        for agent_type, keywords in self.agent_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    agent_scores[agent_type] += 1
        
        # Return specialized agent only if there's a clear match
        best_agent = max(agent_scores.items(), key=lambda x: x[1])
        
        if best_agent[1] > 0:
            logger.info(f"Detected data extraction query, using {best_agent[0]} agent (score: {best_agent[1]})")
            return best_agent[0]
        else:
            logger.info("No specific data extraction detected, using general agent")
            return 'general'
    
    def process_query(self, query: str, agent_type: str = None, use_cache: bool = True, conversation_history: list = None) -> Dict[str, Any]:
        """
        Process a query using the appropriate agent
        
        Args:
            query: User query
            agent_type: Specific agent type to use (optional)
            use_cache: Whether to use cache (default: True)
            conversation_history: Previous conversation messages for context (optional)
            
        Returns:
            Response dictionary
        """
        try:
            # Auto-detect agent type if not specified
            if not agent_type:
                agent_type = self.detect_agent_type(query)
            
            # Validate agent type
            if agent_type not in self.agents:
                agent_type = 'general'
            
            # Check cache first if enabled
            if use_cache:
                cached_result = self.query_cache.get(query, agent_type)
                if cached_result:
                    logger.info(f"Returning cached result for query: {query[:50]}...")
                    return cached_result
            
            # Process query with selected agent
            agent = self.agents[agent_type]
            
            # Check if agent supports conversation history
            if conversation_history and hasattr(agent, 'process_query_with_history'):
                response = agent.process_query_with_history(query, conversation_history)
            else:
                response = agent.process_query(query)
            
            # Add orchestrator metadata
            response.update({
                'orchestrator_version': '1.0',
                'agent_used': agent_type,
                'query_processed_at': self._get_timestamp(),
                'cache_enabled': use_cache,
                'cache_action': 'bypassed' if not use_cache else 'used'
            })
            
            # Cache logic:
            # 1. If use_cache=True and successful -> cache normally
            # 2. If use_cache=False and successful -> OVERWRITE cache with new good response
            if response.get('success', False):
                # Only cache if response is actually useful (not empty/error responses)
                response_text = response.get('response', '').strip()
                is_useful_response = (
                    response_text and 
                    len(response_text) > 50 and
                    '📋 No se encontró información' not in response_text and
                    'Error al procesar' not in response_text
                )
                
                if is_useful_response:
                    if use_cache:
                        # Normal caching - don't overwrite existing entries
                        cache_success = self.query_cache.set(query, response, agent_type, force_overwrite=False)
                        response['cache_action'] = 'stored' if cache_success else 'store_failed'
                    else:
                        # Force overwrite cache with new good response when use_cache=false
                        cache_success = self.query_cache.set(query, response, agent_type, force_overwrite=True)
                        response['cache_action'] = 'overwritten' if cache_success else 'overwrite_failed'
                        logger.info(f"Cache overwritten for query: {query[:50]}... (use_cache=false)")
                else:
                    response['cache_action'] = 'not_cached_poor_quality'
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            return {
                'agent': agent_type or 'unknown',
                'response': f"❌ Error del sistema: {str(e)}",
                'success': False,
                'error': str(e),
                'orchestrator_version': '1.0',
                'query_processed_at': self._get_timestamp()
            }
    
    def refresh_agent_data(self, agent_type: str) -> Dict[str, Any]:
        """
        Refresh data for a specific agent
        
        Args:
            agent_type: Type of agent to refresh
            
        Returns:
            Refresh result
        """
        try:
            if agent_type not in self.agents:
                return {
                    'success': False,
                    'message': f"❌ Tipo de agente no válido: {agent_type}"
                }
            
            # Refresh agent data
            agent = self.agents[agent_type]
            refresh_result = agent.refresh_data()
            
            # Invalidate cache for this agent
            if refresh_result.get('success', False):
                self.query_cache.invalidate_agent_cache(agent_type)
                refresh_result['cache_invalidated'] = True
            
            return refresh_result
            
        except Exception as e:
            logger.error(f"Error refreshing agent {agent_type}: {str(e)}")
            return {
                'agent': agent_type,
                'success': False,
                'message': f"❌ Error al actualizar agente: {str(e)}"
            }
    
    def get_agent_stats(self) -> Dict[str, Any]:
        """Get statistics for all agents"""
        try:
            stats = {
                'orchestrator_version': '1.0',
                'agents': {},
                'cache_stats': self.query_cache.get_cache_stats(),
                'timestamp': self._get_timestamp()
            }
            
            for agent_type, agent in self.agents.items():
                try:
                    agent_stats = agent.get_stats()
                    stats['agents'][agent_type] = agent_stats
                except Exception as e:
                    logger.error(f"Error getting stats for agent {agent_type}: {str(e)}")
                    stats['agents'][agent_type] = {
                        'error': str(e),
                        'agent': agent_type
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting orchestrator stats: {str(e)}")
            return {
                'error': str(e),
                'orchestrator_version': '1.0',
                'timestamp': self._get_timestamp()
            }
    
    def get_available_agents(self) -> Dict[str, Any]:
        """Get list of available agents and their descriptions"""
        return {
            'agents': [
                {
                    'type': 'general',
                    'name': 'Agente General',
                    'description': 'Maneja consultas generales sobre Food Service 2025',
                    'keywords': 'información general, documentos, preguntas generales'
                },
                {
                    'type': 'exhibitors',
                    'name': 'Agente de Expositores',
                    'description': 'Especializado en información de empresas expositoras',
                    'keywords': 'expositores, empresas, stands, marcas'
                },
                {
                    'type': 'visitors',
                    'name': 'Agente de Visitantes',
                    'description': 'Especializado en estadísticas y datos de visitantes',
                    'keywords': 'visitantes, asistencia, demografía, estadísticas'
                }
            ],
            'total_agents': len(self.agents),
            'orchestrator_version': '1.0'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        health = {
            'status': 'healthy',
            'timestamp': self._get_timestamp(),
            'orchestrator_version': '1.0',
            'components': {}
        }
        
        try:
            # Check Redis connection
            health['components']['redis'] = {
                'connected': self.redis_manager.is_connected(),
                'stats': self.redis_manager.get_stats() if self.redis_manager.is_connected() else None
            }
            
            # Check each agent
            for agent_type, agent in self.agents.items():
                try:
                    agent_stats = agent.get_stats()
                    health['components'][f'agent_{agent_type}'] = {
                        'status': 'healthy',
                        'stats': agent_stats
                    }
                except Exception as e:
                    health['components'][f'agent_{agent_type}'] = {
                        'status': 'error',
                        'error': str(e)
                    }
                    health['status'] = 'degraded'
            
            # Overall health status
            failed_components = [k for k, v in health['components'].items() 
                               if v.get('status') == 'error' or not v.get('connected', True)]
            
            if failed_components:
                health['status'] = 'degraded'
                health['failed_components'] = failed_components
            
        except Exception as e:
            health['status'] = 'error'
            health['error'] = str(e)
        
        return health
    
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def clear_cache(self) -> Dict[str, Any]:
        """Clear all cache data"""
        try:
            success = self.query_cache.clear_all_cache()
            return {
                'success': success,
                'message': '✅ Cache limpiado correctamente' if success else '❌ Error al limpiar cache',
                'timestamp': self._get_timestamp()
            }
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return {
                'success': False,
                'message': f'❌ Error al limpiar cache: {str(e)}',
                'timestamp': self._get_timestamp()
            }