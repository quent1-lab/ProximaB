from entity import Entity, Pathfinding
from task import Task, TaskManager
import math, threading, time
from event import AttackEvent

class PNJ(Entity):
    """Classe représentant un PNJ."""
    def __init__(self, x, y, world, size=1.75, speed=1.0):
        super().__init__(x, y, world, size, entity_type="PNJ")
        self.name = self.init_name()
        self.vision_range = 5
        self.speed = speed
        self.target = None
        self.pathfinder = Pathfinding(world)
        self.path = []
        
        self.needs = {'hunger': 100, 'thirst': 100, 'energy': 100}  # Stocker les besoins dans un dictionnaire
        self.needs_threshold = {'hunger': 80, 'thirst': 95, 'energy': 30}  # Seuil de besoin pour déclencher une action
        self.corresponding_actions = {'Food': 'hunger', 'Water': 'thirst'}  # Actions correspondantes pour chaque besoin
        self.finding = [] # Stocker les ressources en cours de recherche
        # Initialisation des attributs de cibles pour chaque besoin
        self.target_hunger = None
        self.target_thirst = None
        
        self.last_attack_time = 0  # Temps de la dernière attaque
        self.attack_cooldown = 1.0  # Délai entre les attaques en secondes
        
        self.collaborators = []  
        self.task_manager = TaskManager(self)

    def init_name(self):
        """Initialise le nom du PNJ."""
        entities_pnj = self.world.entities.get('PNJ', [])
        return f"PNJ {len(entities_pnj) + 1}"

    def update(self, delta_time):
        """Met à jour l'état de l'entité et exécute les tâches."""
        self.update_needs(delta_time)
        self.perform_tasks(delta_time)
        self.task_manager.execute_tasks(delta_time)
        #self.move(delta_time)

    def update_needs(self, delta_time):
        """Mise à jour des besoins naturels."""
        self.needs['hunger'] -= delta_time * 0.3
        self.needs['thirst'] -= delta_time * 0.4
        self.needs['energy'] -= delta_time * 0.05

    def perform_task_based_on_need(self, need_type, search_method, move_method, action_method, threshold, regeneration_rate):
        """Généralise la gestion des tâches en fonction des besoins avec gestion d'attente."""
        # Vérification de la satisfaction du besoin
        if self.needs[need_type] < threshold and need_type not in self.finding and not self.target_hunger and not self.target_thirst:
            # Démarre la recherche de ressource dans un thread à part
            def search_and_set_target():
                search_method()
                if getattr(self, f'target_{need_type}'):
                    # Une fois la ressource trouvée, créer une tâche pour s'y rendre
                    go_to_task = Task(
                        name=f"Aller à {need_type}",
                        action=getattr(self, move_method),
                        priority=100,
                        energy_cost=2
                    )
                    satisfaction_task = Task(
                        name=f"Consommer {need_type}",
                        action=getattr(self, action_method),
                        priority=50,
                        energy_cost=1,
                        regeneration_rate=regeneration_rate
                    )
                    
                    # Ajouter les tâches à la liste des tâches
                    self.task_manager.create_linked_tasks([go_to_task, satisfaction_task])
                    self.finding.remove(need_type)
            
            self.finding.append(need_type)
            threading.Thread(target=search_and_set_target).start()

    def move_to_target(self, delta_time):
        """Déplacement vers la cible."""
        if self.path:
            # Effectue le mouvement et vérifie si la cible est atteinte
            self.move(delta_time)
            if self.is_arrived(self.target):
                self.task_manager.set_task_completed()
    
    def move_to_entity(self, delta_time):
        """Déplacement vers une entité."""
        entity = self.target_hunger
        
        if not entity.is_alive:
            self.task_manager.set_task_completed()
            return
        
        self.path = [(entity.x, entity.y)]
        self.move(delta_time)
        
        if self.get_distance_from(entity.x, entity.y) < 0.5:
            # Attaque l'animal
            self.attack(entity)
                
    def is_at_target(self, target, tol=0.1):
        """Vérifie si le PNJ est arrivé à la cible."""
        return self.get_distance_from(*target) < tol

    def perform_tasks(self, delta_time):
        """Effectue les tâches en fonction des besoins."""
        self.perform_task_based_on_need('hunger', self.find_food, "move_to_entity",'consume_food', self.needs_threshold["hunger"], 20 * delta_time)
        self.perform_task_based_on_need('thirst', self.find_water, "move_to_target",'consume_water', self.needs_threshold["thirst"], 20 * delta_time)
        if self.needs['energy'] < 30:
            self.rest()

    def consume_water(self,delta_time, regeneration_rate):
        """Boit de l'eau pour se réhydrater."""
        self.needs['thirst'] += regeneration_rate
        if self.needs['thirst'] >= 100:
            self.target_thirst = None
            self.task_manager.current_task.complete()

    def consume_food(self,delta_time, regeneration_rate):
        """Mange pour récupérer de la faim."""
        self.needs['hunger'] += regeneration_rate * delta_time * 4
        if self.needs['hunger'] >= 100:
            self.target_hunger = None
            self.task_manager.current_task.complete()

    def attack(self, entity):
        """Attaque une entité."""
        current_time = time.time()
        if current_time - self.last_attack_time >= self.attack_cooldown:
            self.event_manager.emit_event(AttackEvent(self, entity, 10))
            self.last_attack_time = current_time  # Mettre à jour le temps de la dernière attaque
            if not entity.is_alive:
                self.task_manager.set_task_completed()
                #self.world.remove_entity(entity)
    
    def search_resource(self, resource_type):
        """Cherche la ressource la plus proche et la cible."""
        
        if "Food" in resource_type :
            # Cherche l'animal le plus proche et le cible
            self.search_animal(resource_type)
        
        if getattr(self, f'target_{self.corresponding_actions[resource_type]}'):
            return
        
        # Vérifie si sur les cases adjacentes il y a une ressource
        if self.check_adjacent_tiles_for_resource(resource_type):
            self.path = [(self.x, self.y)]
            setattr(self, f'target_{self.corresponding_actions[resource_type]}', (self.x, self.y))
            print(f"{self} est déjà sur la ressource {resource_type}.")
            return
        
        closest_resource = self.find_closest_resource(resource_type)
        if closest_resource:
            adjacent_tile = self.find_adjacent_accessible_tile(closest_resource)
            if adjacent_tile:
                self.set_target(*adjacent_tile)
                setattr(self, f'target_{self.corresponding_actions[resource_type]}', adjacent_tile)
            else:
                print(f"{self} n'a pas trouvé de case adjacente accessible à la ressource {resource_type}.")
        else:
            print(f"{self} n'a pas trouvé de ressource {resource_type} à proximité.")

    def search_animal(self, resource_type):
        """Cherche l'animal le plus proche et le cible."""
        
        list_animal = self.world.entities.get("animal", [])
        closest_animal, closest_distance = None, float('inf')
        for animal in list_animal:
            if animal.is_alive:
                distance = self.get_distance_from(animal.x, animal.y)
                tile_animal = self.world.get_tile_at(animal.x, animal.y)
                if distance < closest_distance and tile_animal.biome != "Water":
                    closest_animal, closest_distance = animal, distance
                
        if closest_animal:
            print(f"Distance de {animal} : {distance} - Biome : {tile_animal.biome}")
            self.set_target(closest_animal.x, closest_animal.y)
            setattr(self, f'target_{self.corresponding_actions[resource_type]}', closest_animal)
        else:
            print(f"{self} n'a pas trouvé d'animal à chasser.")

    def find_water(self):
        """Cherche la source d'eau la plus proche."""
        self.search_resource('Water')

    def find_food(self):
        """Cherche la nourriture la plus proche."""
        # Cherche l'animal le plus proche
        self.search_resource('Food')

    def set_target(self, target_x, target_y):
        """Définit une cible pour le PNJ et lance le calcul du chemin dans un autre thread."""
        self.target = (target_x, target_y)
        self.path = self.pathfinder.a_star((self.x, self.y), self.target)
        self.target = (target_x + 0.5, target_y + 0.5)

    def set_path(self, path):
        """Définit un chemin pour le PNJ."""
        self.path = path

    def move(self, delta_time):
        """Déplace le PNJ vers la cible."""
        if self.path:
            next_pos = self.path[0]
            dx, dy = next_pos[0] - self.x, next_pos[1] - self.y
            distance = math.sqrt(dx ** 2 + dy ** 2)
            if distance > 0:
                self.vx = (dx / distance) * self.speed
                self.vy = (dy / distance) * self.speed
                super().move(delta_time)
    
    def choose_next_move(self):
        """Choisit la prochaine tuile vers laquelle se déplacer en fonction de l'environnement."""
        adjacent_tiles = self.get_adjacent_tiles()
        # Exemple de logique simple : se déplacer vers une tuile sans obstacle
        for tile in adjacent_tiles:
            if tile.biome not in ['Mountains', 'Water']:  # Exemple de biomes à éviter
                return tile.x, tile.y
        return self.x, self.y  # Rester sur place si aucune tuile valide n'est trouvée

    def move2(self, delta_time):
        """Déplace le PNJ vers la cible choisie en temps réel."""
        next_x, next_y = self.choose_next_move()
        dx, dy = next_x - self.x, next_y - self.y
        distance = math.sqrt(dx ** 2 + dy ** 2)
        if distance > 0:
            self.vx = (dx / distance) * self.speed
            self.vy = (dy / distance) * self.speed
            super().move(delta_time)
    
    def check_adjacent_tiles_for_resource(self, resource_type):
        """Vérifie si une ressource est présente dans les cases adjacentes au PNJ."""
        adjacent_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1),
                            (-2, 0), (2, 0), (0, -2), (0, 2),
                            (-1, -1), (-1, 1), (1, -1), (1, 1),
                            (-2, -1), (-2, 1), (2, -1), (2, 1),
                            (-1, -2), (-1, 2), (1, -2), (1, 2),
                            (-2, -2), (-2, 2), (2, -2), (2, 2)]  # Cases adjacentes : droite, gauche, haut, bas, et diagonales
        
        for dx, dy in adjacent_offsets:
            adjacent_x = self.x + dx
            adjacent_y = self.y + dy
            tile = self.world.get_tile_at(adjacent_x, adjacent_y)
            
            if tile and tile.biome == resource_type:
                return True
        
        return False
        
    def find_closest_resource(self, resource_type):
        """Trouve la ressource la plus proche."""
        closest_resource, closest_distance = None, float('inf')
        for chunk in self.world.get_chunks_around(self.x, self.y, radius=2):
            for x, y, tile in chunk.get_tiles():
                if tile.biome == resource_type and not tile.has_entity and not tile.entity_destination:
                    distance = self.get_distance_from(x, y)
                    if distance < closest_distance:
                        closest_resource, closest_distance = (x, y), distance
        return closest_resource
    
    def find_adjacent_accessible_tile(self, resource_tile):
        """Trouve une case adjacente à la ressource qui est accessible."""
        x, y = resource_tile  # Coordonnées de la case avec l'eau
        directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]  # Cases adjacentes : droite, gauche, haut, bas
        for dx, dy in directions:
            adjacent_x, adjacent_y = x + dx, y + dy
            if self.is_tile_accessible(adjacent_x, adjacent_y):
                return adjacent_x, adjacent_y
        return None
    
    def is_tile_accessible(self, x, y):
        """Vérifie si une case est accessible pour le PNJ (non bloquée)."""
        # Ici, on vérifie si la tuile est traversable selon les règles du monde
        tile = self.world.get_tile_at(x, y)
        biome = tile.biome if tile else None
        return biome != 'Water' and biome != 'Obstacle' and not tile.has_entity and not tile.entity_destination  # Exemple: doit être ni eau ni un obstacle

    def get_distance_from(self, x, y):
        """Calcule la distance entre le PNJ et une position donnée."""
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)
    
    def get_adjacent_tiles(self):
        """Retourne les tuiles adjacentes au PNJ."""
        adjacent_tiles = []
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Gauche, Droite, Haut, Bas
        for dx, dy in directions:
            tile_x = self.x + dx
            tile_y = self.y + dy
            chunk_x = int(tile_x // self.config['chunk_size'])
            chunk_y = int(tile_y // self.config['chunk_size'])
            chunk = self.world.get_chunk(chunk_x, chunk_y)
            local_x = int(tile_x % self.config['chunk_size'])
            local_y = int(tile_y % self.config['chunk_size'])
            if 0 <= local_x < self.config['chunk_size'] and 0 <= local_y < self.config['chunk_size']:
                adjacent_tiles.append(chunk.tiles[local_x][local_y])
        return adjacent_tiles
    
    def is_arrived(self,target, tol = 0.1):
        """Vérifie si le PNJ est arrivé à destination."""
        if self.target:
            return math.isclose(self.x, target[0], abs_tol=tol) and math.isclose(self.y, target[1], abs_tol=tol)
        return False

    def rest(self):
        """Récupère de l'énergie."""
        self.needs['energy'] += 10

    def __str__(self) -> str:
        return super().__str__() + f" {self.name}"
