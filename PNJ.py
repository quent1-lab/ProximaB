from entity import Entity, Pathfinding

class PNJ(Entity):
    def __init__(self, x, y, world, size=1.75, speed=1.0):
        super().__init__(x, y, world, size, entity_type="PNJ")
        self.name = self.init_name()
        self.vision_range = 20
        self.speed = speed
        
        self.pathfinder = Pathfinding(world)
        self.behavior_manager = BehaviorManager(self)
        self.memory = PNJMemory()  # Mémoire pour stocker les emplacements des ressources
        
        self.needs = {'hunger': 100, 'thirst': 100, 'energy': 100}
        self.target_location = None

    def update(self, delta_time):
        """Met à jour l'état du PNJ, gère les besoins et exécute des tâches."""
        self.update_needs(delta_time)
        self.behavior_manager.update_behavior(delta_time)
        
        # Explorer la zone autour pour détecter des ressources
        self.explore_and_memorize_resources()

    def update_needs(self, delta_time):
        """Diminue les besoins du PNJ au fil du temps."""
        self.needs['hunger'] -= delta_time * 0.3
        self.needs['thirst'] -= delta_time * 0.4
        self.needs['energy'] -= delta_time * 0.05

    def explore_and_memorize_resources(self):
        """Explore la zone autour et mémorise les ressources découvertes."""
        visible_resources = self.world.get_resources_in_range(self.x, self.y, self.vision_range)
        for resource_type, location in visible_resources.items():
            self.memory.memorize(resource_type, location)

    def move_to(self, target):
        """Déplace le PNJ vers une cible spécifique."""
        self.target_location = target
        if not self.pathfinder.is_target_reached(self.x, self.y, target):
            next_step = self.pathfinder.get_next_step(self.x, self.y, target)
            self.x, self.y = next_step

    def is_at_target(self):
        """Vérifie si le PNJ est à la position cible."""
        return self.pathfinder.is_target_reached(self.x, self.y, self.target_location)

    def consume_water(self, delta_time):
        """Consomme de l'eau pour satisfaire la soif."""
        self.needs['thirst'] += delta_time * 10
        self.needs['thirst'] = min(self.needs['thirst'], 100)

    def consume_food(self, delta_time):
        """Consomme de la nourriture pour satisfaire la faim."""
        self.needs['hunger'] += delta_time * 10
        self.needs['hunger'] = min(self.needs['hunger'], 100)

class BehaviorManager:
    def __init__(self, pnj):
        self.pnj = pnj
        self.current_task = None

    def update_behavior(self, delta_time):
        """Gère les comportements basés sur les besoins et l'environnement."""
        if not self.current_task:
            self.current_task = self.decide_next_task()
        
        if self.current_task:
            self.current_task.execute(delta_time)
            if self.current_task.is_complete():
                self.current_task = None

    def decide_next_task(self):
        """Décide de la prochaine tâche en fonction des besoins et de la mémoire."""
        if self.pnj.needs['thirst'] < 30 and self.pnj.memory.has_resource('Water'):
            return DrinkTask(self.pnj)
        elif self.pnj.needs['hunger'] < 50 and self.pnj.memory.has_resource('Food'):
            return EatTask(self.pnj)
        else:
            return ExploreTask(self.pnj)  # Par défaut, exploration

class Task:
    def __init__(self, pnj):
        self.pnj = pnj
        self.complete = False

    def execute(self, delta_time):
        pass

    def is_complete(self):
        return self.complete

class DrinkTask(Task):
    def execute(self, delta_time):
        if not self.pnj.memory.has_resource('Water'):
            self.pnj.find_water()
        else:
            self.pnj.move_to(self.pnj.memory.get_resource('Water'))
            if self.pnj.is_at_target():
                self.pnj.consume_water(delta_time)
                self.complete = True

class EatTask(Task):
    def execute(self, delta_time):
        if not self.pnj.memory.has_resource('Food'):
            self.pnj.find_food()
        else:
            self.pnj.move_to(self.pnj.memory.get_resource('Food'))
            if self.pnj.is_at_target():
                self.pnj.consume_food(delta_time)
                self.complete = True

class ExploreTask(Task):
    def execute(self, delta_time):
        if self.pnj.is_at_target() or not self.pnj.target_location:
            self.pnj.target_location = self.pnj.get_random_target()
        else:
            self.pnj.move_to(self.pnj.target_location)

class PNJMemory:
    """Mémoire des PNJ pour stocker les emplacements des ressources."""
    def __init__(self):
        self.resources = {}

    def memorize(self, resource_type, location):
        """Ajoute l'emplacement d'une ressource en mémoire."""
        self.resources[resource_type] = location

    def has_resource(self, resource_type):
        """Vérifie si le PNJ se souvient de l'emplacement d'une ressource."""
        return resource_type in self.resources

    def get_resource(self, resource_type):
        """Récupère l'emplacement mémorisé d'une ressource."""
        return self.resources.get(resource_type)
