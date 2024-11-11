from entity import Entity, Pathfinding
from shapely.geometry import Polygon, Point
from event import AttackEvent, DeathEvent, InteractionEvent
import random, math

class PNJ(Entity):
    def __init__(self, x, y, world, size=1.75, speed=1.0):
        super().__init__(x, y, world, size, entity_type="PNJ")
        self.name = self.init_name()
        self.vision_range = 20
        self.speed = speed
        
        self.pathfinder = Pathfinding(world)
        self.behavior_manager = BehaviorManager(self)
        self.memory = PNJMemory(self)  # Mémoire pour stocker les emplacements des ressources
        
        self.needs = {'hunger': 100, 'thirst': 100, 'energy': 100}
        self.target_location = None
        self.actual_chunk = None
        self.actual_chunk_poly = None
        self.path = None

    def init_name(self):
        """Initialise le nom du PNJ."""
        names = [("Alice", "F", (100,20,150)), ("Bob", "M", (20,100,150)), ("Charlie", "M", (150,20,100)), ("Daisy", "F", (40,200,70)), ("Eve", "F", (200,200,20)), ("Frank", "M", (200,100,20)), ("Grace", "F", (20,200,200)), ("Hank", "M", (200,20,200)), ("Ivy", "F", (100,200,20))]
        name = random.choice(names)
        self.color = name[2]
        return name[0]
    
    def update(self, delta_time):
        """Met à jour l'état du PNJ, gère les besoins et exécute des tâches."""
        self.check_pnj_in_chunk()
        self.update_needs(delta_time)
        self.behavior_manager.update_behavior(delta_time)
        super().move(delta_time)
        
        # Explorer la zone autour pour détecter des ressources
        self.explore_and_memorize_view()

    def update_needs(self, delta_time):
        """Diminue les besoins du PNJ au fil du temps."""
        self.needs['hunger'] -= delta_time * 0.3
        self.needs['thirst'] -= delta_time * 0.4
        self.needs['energy'] -= delta_time * 0.05

    def explore_and_memorize_view(self):
        """Utilise le champ de vision pour mémoriser les zones visibles."""
        self.memory.memorize_chunk(self.actual_chunk.x, self.actual_chunk.y)

    def cast_rays(self, vision_range, angle):
        """Retourne une liste de points visibles en utilisant un casting de rayons."""
        visible_points = []
        step_angle = 5  # Étape de l'angle pour chaque rayon
        half_angle = int(angle / 2)  # Convertir en entier

        for i in range(-half_angle, half_angle + 1, step_angle):
            rad_angle = math.radians(i)
            dir_x = self.direction[0] * math.cos(rad_angle) - self.direction[1] * math.sin(rad_angle)
            dir_y = self.direction[0] * math.sin(rad_angle) + self.direction[1] * math.cos(rad_angle)
            point = self.cast_single_ray(dir_x, dir_y, vision_range)
            if point:
                visible_points.append(point)
        
        return visible_points

    def cast_single_ray(self, dir_x, dir_y, range_vision):
        """Simule un seul rayon dans une direction donnée jusqu'à une distance maximale."""
        x, y = self.x, self.y
        for i in range(range_vision):
            x += dir_x
            y += dir_y
            if not self.is_passable(x, y):
                return (x, y)
        return (x, y)

    def is_passable(self, x, y):
        """Vérifie si la tuile à la position (x, y) est passable."""
        chunk = self.world.get_chunk_from_position(x, y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])
        if 0 <= local_x < self.config['chunk_size'] and 0 <= local_y < self.config['chunk_size']:
            tile = chunk.tiles[local_x][local_y]
            return tile.biome not in ['Water','Mountains']
        return False
    
    def is_in_chunk(self, x, y):
        """Vérifie si une position spécifique est dans le chunk actuel du PNJ."""
        if not self.actual_chunk_poly:
            return False
        return self.actual_chunk_poly.contains(Point(x, y))
    
    def set_chunk_actual(self):
        """Définit le chunk actuel du PNJ en fonction de sa position actuelle."""
        chunk_x = int(self.x // self.config['chunk_size'])
        chunk_y = int(self.y // self.config['chunk_size'])
        chunk_size = self.config['chunk_size']
        self.actual_chunk_poly = Polygon([(chunk_x, chunk_y), (chunk_x * chunk_size + chunk_size, chunk_y),
                                     (chunk_x * chunk_size + chunk_size, chunk_y * chunk_size + chunk_size),
                                     (chunk_x, chunk_y * chunk_size + chunk_size)])
        self.actual_chunk = self.world.get_chunk(chunk_x, chunk_y)
    
    def check_pnj_in_chunk(self):
        """Vérifie si le PNJ est toujours dans le chunk actuel."""
        if not self.is_in_chunk(self.x, self.y):
            self.set_chunk_actual()

    def move_to(self):
        """Déplace le PNJ vers une cible spécifique en fonction de son environnement."""
        target = self.target_location
        
        if self.path:
            self.follow_path()
            return
        
        if target and not self.is_at_target():
            # Calculer le vecteur de direction vers la cible
            dir_x = target[0] - self.x
            dir_y = target[1] - self.y
            distance = math.sqrt(dir_x ** 2 + dir_y ** 2)
            
            if distance > 0:
                # Normaliser le vecteur de direction
                dir_x /= distance
                dir_y /= distance
                
                # Vérifier si le chemin est passable
                next_x = self.x + dir_x * 0.8
                next_y = self.y + dir_y * 0.8
                if self.is_passable(next_x, next_y):
                    # Mettre à jour la vitesse pour des déplacements fluides
                    self.vx = dir_x * self.speed
                    self.vy = dir_y * self.speed
                else:
                    # Si le chemin n'est pas passable, éviter l'obstacle
                    self.path = self.pathfinder.a_star((self.x, self.y), target, self.vision_range)
            else:
                # Si déjà à la cible, arrêter le PNJ
                self.vx = 0
                self.vy = 0
        else:
            self.vx = 0
            self.vy = 0
    
    def follow_path(self):
        """Déplace le PNJ le long du chemin calculé par l'algorithme A*."""
        if self.path:
            next_node = self.path[0]
            target = (next_node[0], next_node[1])
            self.calculate_velocity(target)
            
            if self.is_at_target(target):
                self.path.pop(0)
        
    def calculate_velocity(self, target):
        """Calcule le vecteur de direction vers la cible et met à jour la vitesse."""
        dir_x = target[0] - self.x
        dir_y = target[1] - self.y
        distance = math.sqrt(dir_x ** 2 + dir_y ** 2)
        
        if distance > 0:
            dir_x /= distance
            dir_y /= distance
            self.vx = dir_x * self.speed
            self.vy = dir_y * self.speed
        else:
            self.vx = 0
            self.vy = 0
    
    def distance(self, x1, y1, x2, y2):
        """Calcule la distance euclidienne entre deux points."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

    def avoid_obstacle(self):
        """Évite les obstacles en trouvant une direction alternative."""
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)]
        best_direction = (0, 0)
        min_distance = float('inf')
        target = self.target_location
        
        for dx, dy in directions:
            next_x = self.x + dx
            next_y = self.y + dy
            if self.is_passable(next_x, next_y):
                dist = self.distance(next_x, next_y, target[0], target[1])
                if dist < min_distance:
                    min_distance = dist
                    best_direction = (dx, dy)

        return best_direction

    def get_random_target(self):
        """Génère une position cible aléatoire dans le monde, privilégiant les chunks non connus."""
        max_attempts = 100  # Nombre maximum de tentatives pour trouver un chunk non connu
        for _ in range(max_attempts):
            target_x = random.randint(int(self.x - self.vision_range), int(self.x + self.vision_range))
            target_y = random.randint(int(self.y - self.vision_range), int(self.y + self.vision_range))
            chunk_x = target_x // self.config['chunk_size']
            chunk_y = target_y // self.config['chunk_size']
            if not self.memory.is_chunk_known(chunk_x, chunk_y):
                if self.is_passable(target_x, target_y):
                    return (target_x, target_y)
                
        # Si toutes les tentatives échouent, retourner une position aléatoire
        target = (random.randint(int(self.x - self.vision_range), int(self.x + self.vision_range)),
                  random.randint(int(self.y - self.vision_range), int(self.y + self.vision_range)))
        while not self.is_passable(target[0], target[1]):
            target = (random.randint(int(self.x - self.vision_range), int(self.x + self.vision_range)),
                      random.randint(int(self.y - self.vision_range), int(self.y + self.vision_range)))
        return target
    
    def is_at_target(self,target=None, threshold=0.1):
        """Vérifie si le PNJ est à la position cible."""
        if not target:
            target = self.target_location
        if not target:
            return False
        distance = math.sqrt((self.x - target[0]) ** 2 + (self.y - target[1]) ** 2) 
        return distance < threshold + self.size / 2

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
        if self.pnj.needs['thirst'] < 40 and self.pnj.memory.has_resource('Water'):
            print(f"{self.pnj.name} a soif !")
            return DrinkTask(self.pnj)
        elif self.pnj.needs['hunger'] < 95:
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
    def __init__(self,pnj):
        super().__init__(pnj)
        self.target = None
        self.pnj = pnj
        
    def execute(self, delta_time):
        if not self.pnj.memory.has_resource('Water'):
            self.pnj.find_water()
        else:
            # Trouve la ressource en eau la plus proche
            if not self.target:
                self.target = self.pnj.memory.get_resource('Water')
                self.pnj.target_location = self.target
            
            self.pnj.move_to()
            if self.pnj.is_at_target():
                self.pnj.consume_water(delta_time)
                if self.pnj.needs['thirst'] >= 100:
                    self.complete = True

class EatTask(Task):
    def __init__(self, pnj):
        super().__init__(pnj)
        self.target = None
        self.food = None
        self.pnj = pnj
        self.attack_cooldown = 0  # Temps restant avant la prochaine attaque
        self.attack_delay = 2  # Délai entre les attaques en secondes
    
    def execute(self, delta_time):
        if not self.pnj.memory.has_resource('Food') and not self.target:
            self.find_animal()
        else:
            self.attack_animal(delta_time)
            if self.food:
                self.pnj.consume_food(delta_time)
                if self.pnj.needs['hunger'] >= 100:
                    self.complete = True
                    self.pnj.target_location = None
    
    def find_animal(self):
        """Trouve un animal à chasser pour obtenir de la nourriture."""
        animals = self.pnj.world.entities.get("animal", [])
        if animals:
            # Choisir l'animal le plus proche
            min_distance = float('inf')
            closest_animal = None
            for animal in animals:
                if not animal.is_alive:
                    continue
                distance = math.sqrt((self.pnj.x - animal.x) ** 2 + (self.pnj.y - animal.y) ** 2)
                if distance < min_distance:
                    min_distance = distance
                    closest_animal = animal
            self.target = closest_animal
        else:
            self.complete = True
    
    def attack_animal(self, delta_time):
        """Attaque l'animal le plus proche pour obtenir de la nourriture."""
        if self.target:
            distance = math.sqrt((self.pnj.x - self.target.x) ** 2 + (self.pnj.y - self.target.y) ** 2)
            if distance < 2:
                if self.attack_cooldown <= 0:
                    self.pnj.event_manager.emit_event(AttackEvent(self.pnj, self.target, 10))
                    self.attack_cooldown = self.attack_delay  # Réinitialiser le délai d'attaque
                    if self.target.health <= 0:
                        self.food = True
                else:
                    self.attack_cooldown -= delta_time  # Décrémenter le délai d'attaque
            
            self.pnj.target_location = (self.target.x, self.target.y)
            self.pnj.move_to()

class ExploreTask(Task):
    def execute(self, delta_time):
        if self.pnj.is_at_target():
            self.complete = True
            self.pnj.target_location = None
        elif not self.pnj.target_location:
            self.pnj.target_location = self.pnj.get_random_target()
        else:
            self.pnj.move_to()

class PNJMemory:
    def __init__(self, pnj):
        """Mémoire des PNJ pour stocker les chunks découverts."""
        self.discovered_chunks = set()  # Ensemble des coordonnées des chunks connus
        self.resources = {}  # Dictionnaire des ressources connues
        self.pnj = pnj

    def memorize_chunk(self, chunk_x, chunk_y):
        """Mémorise la position d'un chunk découvert."""
        if self.discovered_chunks:
            if (chunk_x, chunk_y) not in self.discovered_chunks:
                self.discovered_chunks.add((chunk_x, chunk_y))
                self.memorize_resource(self.pnj.world.get_chunk(chunk_x, chunk_y))
        else:
            self.discovered_chunks.add((chunk_x, chunk_y))
            self.memorize_resource(self.pnj.world.get_chunk(chunk_x, chunk_y))

    def memorize_resource(self, chunk):
        """Mémorise la position d'une ressource spécifique."""
        for resource, tiles in chunk.biome_info.items():
            if resource in self.resources:
                self.resources[resource].update(tiles)
            else:
                self.resources[resource] = set(tiles)

    def is_chunk_known(self, chunk_x, chunk_y):
        """Vérifie si un chunk spécifique est déjà connu."""
        return (chunk_x, chunk_y) in self.discovered_chunks

    def get_all_discovered_chunks(self):
        """Retourne la liste des chunks découverts."""
        return list(self.discovered_chunks)

    def has_resource(self, resource_type):
        """Vérifie si une ressource spécifique est connue."""
        return resource_type in self.resources

    def find_resource(self, resource_type):
        """Retourne la position la plus proche de la ressource spécifique."""
        if resource_type in self.resources:
            min_distance = float('inf')
            min_position = None
            for position in self.resources[resource_type]:
                distance = math.sqrt((self.pnj.x - position[0]) ** 2 + (self.pnj.y - position[1]) ** 2)
                if distance < min_distance:
                    min_distance = distance
                    min_position = position
            return self.accessible_resource(min_position)
        return None
    
    def accessible_resource(self, target):
        """Retourne une position accessible à partir de la position cible."""
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        for dx, dy in directions:
            x, y = target[0] + dx, target[1] + dy
            chunk = self.pnj.world.get_chunk_from_position(x, y)
            if chunk.tiles[x - chunk.x_offset][y - chunk.y_offset].biome != "Water":
                return (x+0.5, y+0.5)
        return None
    
    def get_resource(self, resource_type):
        """Retourne la position de la ressource spécifique."""
        if resource_type in self.resources:
            return self.find_resource(resource_type)
        return None

