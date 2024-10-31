class Event:
    def __init__(self, event_type, source, target=None, data=None):
        self.type = event_type  # Le type d'événement, ex: "collision", "interaction"
        self.source = source    # L'entité ou l'objet qui déclenche l'événement
        self.target = target    # L'entité ou l'objet cible de l'événement, si applicable
        self.data = data        # Données supplémentaires, si nécessaire

class EventManager:
    def __init__(self):
        self.listeners = {}  # Dictionnaire des écouteurs par type d'événement

    def register_listener(self, event_type, listener):
        """Ajoute un listener pour un type d'événement spécifique."""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(listener)

    def emit_event(self, event):
        """Envoie un événement à tous les listeners inscrits pour ce type d'événement."""
        if event.type in self.listeners:
            for listener in self.listeners[event.type]:
                listener(event)

class InteractionEvent(Event):
    def __init__(self, source, target, data=None):
        super().__init__("interaction", source, target, data)

class CollisionEvent(Event):
    def __init__(self, source, target, impact_force=None):
        super().__init__("collision", source, target, {"impact_force": impact_force})

class AttackEvent(Event):
    def __init__(self, source, target, damage):
        super().__init__("attack", source, target, {"damage": damage})

class DeathEvent(Event):
    def __init__(self, source, target):
        super().__init__("death", source, target)