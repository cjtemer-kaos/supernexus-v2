"""
Workers estándar — Las gemas con código Python dedicado:
  - AyudaGem:        guía reactiva del sistema, perfil de usuario
  - ScholarGem:      investigación web multi-backend
  - SageGem:         persistencia de conocimiento (memoria)
  - BibliotecaGem:   organización de conocimiento (knowledge base)
  - PrompterGem:     prompt engineering con knowledge base de 13 templates
                     + 37 credit-killing patterns (nidhinjs/prompt-master v1.6.0, MIT)
  - WebResearchGem:  crawling + ranking de páginas web (v1.6.0, port RUFUS primitives)

Cada uno implementa GemaBase y es overridable por gemas_client_overrides
del proyecto cliente.
"""
from .ayuda import AyudaGem
from .scholar import ScholarGem
from .sage import SageGem
from .biblioteca import BibliotecaGem
from .prompter import PrompterGem
from .web_research import WebResearchGem

__all__ = [
    "AyudaGem", "ScholarGem", "SageGem", "BibliotecaGem", "PrompterGem",
    "WebResearchGem",
]
