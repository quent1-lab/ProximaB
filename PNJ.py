from entity import Entity, Pathfinding
from shapely.geometry import Polygon, MultiPoint
import random, math

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

    def init_name(self):
        """Initialise le nom du PNJ."""
        names = ['Alice', 'Bob', 'Charlie', 'David', 'Eve', 'Frank', 'Grace', 'Hank', 'Ivy', 'Jack']
        return random.choice(names)
    
    def update(self, delta_time):
        """Met à jour l'état du PNJ, gère les besoins et exécute des tâches."""
        self.update_needs(delta_time)
        self.behavior_manager.update_behavior(delta_time)
        super().move(delta_time)
        
        # Explorer la zone autour pour détecter des ressources
        self.explore_and_memorize_resources()

    def update_needs(self, delta_time):
        """Diminue les besoins du PNJ au fil du temps."""
        self.needs['hunger'] -= delta_time * 0.3
        self.needs['thirst'] -= delta_time * 0.4
        self.needs['energy'] -= delta_time * 0.05

    def explore_and_memorize_resources(self):
        """Explore l'environnement et mémorise les ressources visibles."""
        visible_chunk = self.world.get_chunks_around(self.x, self.y, 1)
        for chunk in visible_chunk:
            chunk_x = chunk.x_offset
            chunk_y = chunk.y_offset
            self.memory.memorize_chunk(chunk_x, chunk_y, self.config['chunk_size'])

    def move_to(self, target):
        """Déplace le PNJ vers une cible spécifique en fonction de son environnement."""
        self.target_location = target
        if not self.pathfinder.is_target_reached(self.x, self.y, target):
            # Analyser l'environnement immédiat
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Gauche, Droite, Haut, Bas
            best_direction = None
            min_distance = float('inf')

            for dx, dy in directions:
                new_x = self.x + dx
                new_y = self.y + dy
                if self.is_passable(new_x, new_y):
                    distance = math.sqrt((target[0] - new_x) ** 2 + (target[1] - new_y) ** 2)
                    if distance < min_distance:
                        min_distance = distance
                        best_direction = (dx, dy)

            if best_direction:
                # Mise à jour de vx, vy
                self.vx = best_direction[0] * self.speed
                self.vy = best_direction[1] * self.speed
        else:
            self.vx = 0
            self.vy = 0

    def is_passable(self, x, y):
        """Vérifie si la tuile à la position (x, y) est passable."""
        chunk_x = int(x // self.config['chunk_size'])
        chunk_y = int(y // self.config['chunk_size'])
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])
        if 0 <= local_x < self.config['chunk_size'] and 0 <= local_y < self.config['chunk_size']:
            tile = chunk.tiles[local_x][local_y]
            return tile.biome not in ['Mountains', 'Water']  # Exemple de biomes non passables
        return False
    
    def get_random_target(self):
        """Génère une position cible aléatoire dans le monde, privilégiant les chunks non connus."""
        max_attempts = 100  # Nombre maximum de tentatives pour trouver un chunk non connu
        for _ in range(max_attempts):
            target_x = random.randint(int(self.x - self.vision_range), int(self.x + self.vision_range))
            target_y = random.randint(int(self.y - self.vision_range), int(self.y + self.vision_range))
            chunk_x = target_x // self.config['chunk_size']
            chunk_y = target_y // self.config['chunk_size']
            if not self.memory.is_chunk_known(chunk_x, chunk_y):
                return (target_x, target_y)
        # Si toutes les tentatives échouent, retourner une position aléatoire
        return (self.x + random.randint(-100, 100), self.y + random.randint(-100, 100))

    def is_at_target(self):
        """Vérifie si le PNJ est à la position cible."""
        if not self.target_location:
            return False
        return self.pathfinder.is_target_reached(self.x, self.y, self.target_location)

    def consume_water(self, delta_time):
        """Consomme de l'eau pour satisfaire la soif."""
        self.needs['thirst'] += delta_time * 10
        self.needs['thirst'] = min(self.needs['thirst'], 100)

    def consume_food(self, delta_time):
        """Consomme de la nourriture pour satisfaire la faim."""
        self.needs['hunger'] += delta_time * 10
        self.needs['hunger'] = min(self.needs['hunger'], 100)

    def __str__(self):
        return f"PNJ {self.name} -" + super().__str__()
    
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
        if self.pnj.needs['thirst'] < 90 and self.pnj.memory.has_resource('Water'):
            print(f"{self.pnj.name} a soif ! - {self.pnj.memory.get_resource('Water')}")
            return DrinkTask(self.pnj)
        elif self.pnj.needs['hunger'] < 70 and self.pnj.memory.has_resource('Food'):
            print(f"{self.pnj.name} a faim !")
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
            # Trouve la ressource en eau la plus proche
            target = None
            min_distance = float('inf')
            for resource in self.pnj.memory.resources["Water"]:
                distance = math.sqrt((self.pnj.x - resource[0]) ** 2 + (self.pnj.y - resource[1]) ** 2)
                if distance < min_distance:
                    min_distance = distance
                    target = resource
            print(f"{self.pnj.name} se dirige vers la ressource en eau la plus proche : {target}")
            self.pnj.move_to(target)
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
        if self.pnj.is_at_target():
            self.complete = True
            self.pnj.target_location = None
        elif not self.pnj.target_location:
            self.pnj.target_location = self.pnj.get_random_target()
        else:
            self.pnj.move_to(self.pnj.target_location)

class PNJMemory:
    """Mémoire des PNJ pour stocker les emplacements des ressources et des chunks découverts."""
    def __init__(self):
        self.resources = {}
        self.discovered_chunks = set()  # Ensemble des chunks découverts
        self.chunk_size = None  # Taille des chunks, à définir lors de la première mémorisation

    def memorize_chunk(self, chunk_x, chunk_y, chunk_size):
        """Mémorise un chunk découvert et met à jour les limites de la zone connue."""
        self.discovered_chunks.add((chunk_x, chunk_y))
        if self.chunk_size is None:
            self.chunk_size = chunk_size

    def is_chunk_known(self, chunk_x, chunk_y):
        """Vérifie si un chunk est dans la zone connue."""
        return (chunk_x, chunk_y) in self.discovered_chunks

    def get_discovered_area(self):
        """Retourne les limites précises de la zone découverte sous forme de polygone."""
        if not self.discovered_chunks or self.chunk_size is None:
            return None

        points = []
        for chunk_x, chunk_y in self.discovered_chunks:
            x1, y1 = chunk_x, chunk_y
            x2, y2 = x1 + self.chunk_size, y1 + self.chunk_size
            points.extend([(x1, y1), (x1, y2), (x2, y1), (x2, y2)])

        # Utiliser shapely pour créer un polygone à partir des points
        polygon = MultiPoint(points).convex_hull
        return polygon
