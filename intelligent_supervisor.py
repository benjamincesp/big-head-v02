"""
Intelligent Supervisor for Food Service 2025 Multi-Agent System
Acts as a smart router that analyzes queries and selects the best agent
"""

import logging
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from openai_client import get_openai_client
from exceptions import OpenAIError, AgentError

logger = logging.getLogger(__name__)

class AgentType(Enum):
    GENERAL = "general"
    EXHIBITORS = "exhibitors" 
    VISITORS = "visitors"

@dataclass
class RoutingDecision:
    selected_agent: AgentType
    confidence: float
    reasoning: str
    keywords_matched: List[str]
    context_analysis: str

class IntelligentSupervisor:
    """
    Intelligent supervisor that analyzes queries and routes them to the most appropriate agent
    Uses advanced NLP analysis and contextual understanding for optimal routing decisions
    """
    
    def __init__(self, openai_api_key: str):
        """Initialize the intelligent supervisor"""
        print("🧠 DEBUG: IntelligentSupervisor - Initializing...")
        
        try:
            self.openai_client = get_openai_client(openai_api_key)
            print("🧠 DEBUG: IntelligentSupervisor - OpenAI client initialized")
        except Exception as e:
            print(f"❌ DEBUG: IntelligentSupervisor - OpenAI client failed: {str(e)}")
            raise AgentError(f"Failed to initialize OpenAI client: {str(e)}")
            
        # Enhanced keyword patterns for better agent detection
        self.agent_patterns = {
            AgentType.EXHIBITORS: {
                'primary_keywords': [
                    'expositores', 'empresas', 'stands', 'marcas', 'compañías',
                    'participantes comerciales', 'directorio empresas', 'catálogo expositores',
                    'lista empresas', 'nombres empresas', 'cuántas empresas',
                    'stands asignados', 'números stand', 'ubicación stands',
                    'productos exhibidos', 'servicios expositores', 'contacto empresas'
                ],
                'secondary_keywords': [
                    'comercial', 'venta', 'producto', 'servicio', 'negocio',
                    'proveedor', 'distribuidor', 'marca comercial', 'empresa participante'
                ],
                'question_patterns': [
                    r'qué empresas',
                    r'cuáles empresas',
                    r'lista.*empresas',
                    r'directorio.*expositores',
                    r'stands.*ubicados',
                    r'empresas.*participan'
                ]
            },
            
            AgentType.VISITORS: {
                'primary_keywords': [
                    'visitantes', 'asistentes', 'público', 'asistencia', 'audiencia',
                    'cuántos visitantes', 'número asistentes', 'cantidad público',
                    'estadísticas visitantes', 'demografía', 'perfil visitantes',
                    'datos asistencia', 'cifras público', 'análisis audiencia',
                    'tendencias asistencia', 'crecimiento visitantes'
                ],
                'secondary_keywords': [
                    'profesionales', 'sector', 'industria', 'perfil demográfico',
                    'networking', 'conexiones', 'participación', 'registro'
                ],
                'question_patterns': [
                    r'cuántos.*visitantes',
                    r'cuánta.*gente',
                    r'número.*asistentes',
                    r'estadísticas.*público',
                    r'demografía.*visitantes',
                    r'perfil.*asistentes'
                ]
            },
            
            AgentType.GENERAL: {
                'primary_keywords': [
                    'información general', 'qué es', 'cómo funciona', 'cuándo',
                    'dónde', 'inscripción', 'registro', 'participar',
                    'food service', 'evento', 'feria', 'espacio food',
                    'historia evento', 'objetivos', 'beneficios', 'actividades'
                ],
                'secondary_keywords': [
                    'ayuda', 'información', 'detalles', 'explicación',
                    'orientación', 'guía', 'soporte', 'consulta general'
                ],
                'question_patterns': [
                    r'qué.*food service',
                    r'cómo.*participar',
                    r'cuándo.*evento',
                    r'dónde.*realiza',
                    r'qué.*haces',
                    r'ayuda.*con',
                    r'información.*sobre'
                ]
            }
        }
        
        # Context analysis patterns
        self.context_indicators = {
            'data_extraction': [
                'cuántos', 'cuántas', 'número', 'cantidad', 'lista', 'nombres',
                'directorio', 'catálogo', 'estadísticas', 'cifras', 'datos'
            ],
            'informational': [
                'qué es', 'cómo', 'por qué', 'para qué', 'cuándo', 'dónde',
                'información', 'explica', 'describe', 'ayuda'
            ],
            'commercial': [
                'empresas', 'marcas', 'productos', 'servicios', 'stands',
                'expositores', 'comercial', 'negocios'
            ],
            'demographic': [
                'visitantes', 'asistentes', 'público', 'demografía', 'perfil',
                'audiencia', 'asistencia', 'profesionales'
            ]
        }
        
        print("✅ DEBUG: IntelligentSupervisor initialization complete")
    
    def analyze_query_with_ai(self, query: str) -> Dict[str, Any]:
        """Use AI to analyze query intent and context"""
        try:
            analysis_prompt = f"""
            Analiza la siguiente consulta sobre Food Service 2025 y determina:
            
            1. INTENT: ¿Cuál es la intención principal?
               - DATA_EXTRACTION: Busca datos específicos, números, listas
               - INFORMATION: Busca información general, explicaciones
               - COMMERCIAL: Se enfoca en aspectos comerciales/empresariales
               - DEMOGRAPHIC: Se enfoca en visitantes/asistencia
            
            2. DOMAIN: ¿A qué dominio pertenece principalmente?
               - EXHIBITORS: Empresas, expositores, stands, aspectos comerciales
               - VISITORS: Visitantes, asistencia, demografía, estadísticas de público
               - GENERAL: Información general del evento, participación, orientación
            
            3. KEYWORDS: Identifica las palabras clave más relevantes
            
            4. CONFIDENCE: Del 1-10, qué tan seguro estás de la clasificación
            
            Consulta: "{query}"
            
            Responde en formato JSON:
            {{
                "intent": "DATA_EXTRACTION|INFORMATION|COMMERCIAL|DEMOGRAPHIC",
                "domain": "EXHIBITORS|VISITORS|GENERAL",
                "keywords": ["palabra1", "palabra2", ...],
                "confidence": 8,
                "reasoning": "Explicación breve de por qué esta clasificación"
            }}
            """
            
            messages = [
                {"role": "system", "content": "Eres un experto analizador de consultas para Food Service 2025. Responde SOLO en formato JSON."},
                {"role": "user", "content": analysis_prompt}
            ]
            
            response_data = self.openai_client.chat_completion(
                messages=messages,
                model="gpt-4o-mini",
                max_tokens=300,
                temperature=0.1
            )
            
            import json
            analysis = json.loads(response_data["content"])
            return analysis
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            return {
                "intent": "INFORMATION",
                "domain": "GENERAL", 
                "keywords": [],
                "confidence": 5,
                "reasoning": "Fallback due to analysis error"
            }
    
    def calculate_keyword_score(self, query: str, agent_type: AgentType) -> Tuple[float, List[str]]:
        """Calculate keyword matching score for an agent"""
        query_lower = query.lower()
        patterns = self.agent_patterns[agent_type]
        matched_keywords = []
        
        # Primary keywords (higher weight)
        primary_score = 0
        for keyword in patterns['primary_keywords']:
            if keyword in query_lower:
                primary_score += 2.0
                matched_keywords.append(keyword)
        
        # Secondary keywords (lower weight)
        secondary_score = 0
        for keyword in patterns['secondary_keywords']:
            if keyword in query_lower:
                secondary_score += 1.0
                matched_keywords.append(keyword)
        
        # Pattern matching (highest weight)
        pattern_score = 0
        for pattern in patterns['question_patterns']:
            if re.search(pattern, query_lower):
                pattern_score += 3.0
                matched_keywords.append(f"pattern:{pattern}")
        
        total_score = primary_score + secondary_score + pattern_score
        return total_score, matched_keywords
    
    def analyze_context(self, query: str) -> Dict[str, float]:
        """Analyze query context indicators"""
        query_lower = query.lower()
        context_scores = {}
        
        for context_type, indicators in self.context_indicators.items():
            score = 0
            for indicator in indicators:
                if indicator in query_lower:
                    score += 1
            context_scores[context_type] = score
            
        return context_scores
    
    def route_query(self, query: str) -> RoutingDecision:
        """
        Intelligently route query to the best agent
        
        Args:
            query: User query to analyze
            
        Returns:
            RoutingDecision with selected agent and reasoning
        """
        try:
            print(f"🧠 DEBUG: Analyzing query: {query[:100]}...")
            
            # Step 1: AI-powered analysis
            ai_analysis = self.analyze_query_with_ai(query)
            print(f"🧠 DEBUG: AI Analysis - Domain: {ai_analysis['domain']}, Intent: {ai_analysis['intent']}")
            
            # Step 2: Calculate keyword scores for each agent
            agent_scores = {}
            all_matched_keywords = {}
            
            for agent_type in AgentType:
                score, keywords = self.calculate_keyword_score(query, agent_type)
                agent_scores[agent_type] = score
                all_matched_keywords[agent_type] = keywords
                print(f"🧠 DEBUG: {agent_type.value} score: {score}, keywords: {keywords}")
            
            # Step 3: Context analysis
            context_scores = self.analyze_context(query)
            print(f"🧠 DEBUG: Context scores: {context_scores}")
            
            # Step 4: Combine AI analysis with keyword scoring
            final_scores = {}
            
            for agent_type in AgentType:
                base_score = agent_scores[agent_type]
                
                # AI domain boost
                if ai_analysis['domain'] == agent_type.value.upper():
                    base_score += 5.0
                
                # Context boost
                if agent_type == AgentType.EXHIBITORS and context_scores.get('commercial', 0) > 0:
                    base_score += context_scores['commercial'] * 1.5
                elif agent_type == AgentType.VISITORS and context_scores.get('demographic', 0) > 0:
                    base_score += context_scores['demographic'] * 1.5
                elif agent_type == AgentType.GENERAL and context_scores.get('informational', 0) > 0:
                    base_score += context_scores['informational'] * 1.2
                
                final_scores[agent_type] = base_score
            
            # Step 5: Select best agent
            best_agent = max(final_scores.items(), key=lambda x: x[1])
            selected_agent = best_agent[0]
            max_score = best_agent[1]
            
            # Calculate confidence (0-1 scale)
            total_possible_score = max(10.0, max_score + 5.0)  # Avoid division by zero
            confidence = min(1.0, max_score / total_possible_score)
            
            # Handle low confidence - default to general agent
            if confidence < 0.3 or max_score < 2.0:
                selected_agent = AgentType.GENERAL
                confidence = 0.7  # Medium confidence for general fallback
                reasoning = f"Low confidence in specialized routing (max_score: {max_score:.1f}), defaulting to general agent for comprehensive response"
            else:
                reasoning = f"Selected {selected_agent.value} agent based on AI analysis (domain: {ai_analysis['domain']}) and keyword matching (score: {max_score:.1f})"
            
            decision = RoutingDecision(
                selected_agent=selected_agent,
                confidence=confidence,
                reasoning=reasoning,
                keywords_matched=all_matched_keywords[selected_agent],
                context_analysis=f"Intent: {ai_analysis['intent']}, Context: {context_scores}"
            )
            
            print(f"✅ DEBUG: Routing decision - Agent: {selected_agent.value}, Confidence: {confidence:.2f}")
            return decision
            
        except Exception as e:
            logger.error(f"Error in query routing: {str(e)}")
            # Fallback to general agent
            return RoutingDecision(
                selected_agent=AgentType.GENERAL,
                confidence=0.5,
                reasoning=f"Fallback to general agent due to routing error: {str(e)}",
                keywords_matched=[],
                context_analysis="Error during analysis"
            )
    
    def get_routing_explanation(self, decision: RoutingDecision) -> str:
        """Generate human-readable explanation of routing decision"""
        explanation = f"""
🧠 **Decisión de Enrutamiento Inteligente**

**Agente Seleccionado:** {decision.selected_agent.value.title()}
**Nivel de Confianza:** {decision.confidence:.0%}

**Razonamiento:** {decision.reasoning}

**Palabras Clave Identificadas:** {', '.join(decision.keywords_matched) if decision.keywords_matched else 'Ninguna específica'}

**Análisis de Contexto:** {decision.context_analysis}
        """
        return explanation.strip()
    
    def get_supervisor_stats(self) -> Dict[str, Any]:
        """Get supervisor statistics and configuration"""
        return {
            "supervisor_version": "1.0",
            "available_agents": [agent.value for agent in AgentType],
            "routing_strategies": [
                "AI-powered intent analysis",
                "Keyword pattern matching", 
                "Context analysis",
                "Confidence-based fallback"
            ],
            "total_patterns": sum(
                len(patterns['primary_keywords']) + 
                len(patterns['secondary_keywords']) + 
                len(patterns['question_patterns'])
                for patterns in self.agent_patterns.values()
            )
        }