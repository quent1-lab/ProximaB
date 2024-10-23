from entity import Entity, Pathfinding
from task import Task, TaskManager
import math, threading

class PNJ(Entity):
    """Classe représentant un PNJ."""
    def __init__(self, x, y, world, config, id, size=1.75, speed=1.0):
        super().__init__(x, y, world, config, size, entity_type="PNJ")
        self.id = id
        self.name = self.init_name()
        self.speed = speed
        self.target = None
        self.pathfinder = Pathfinding(world)
        self.path = []
        
        self.needs = {'hunger': 100, 'thirst': 100, 'energy': 100}  # Stocker les besoins dans un dictionnaire
        self.needs_threshold = {'hunger': 20, 'thirst': 20, 'energy': 30}  # Seuil de besoin pour déclencher une action
        self.corresponding_actions = {'Food': 'hunter', 'Water': 'thirst'}  # Actions correspondantes pour chaque besoin
        self.finding = [] # Stocker les ressources en cours de recherche
        # Initialisation des attributs de cibles pour chaque besoin
        self.target_hunger = None
        self.target_thirst = None
        
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
        self.needs['hunger'] -= delta_time * 0.1
        self.needs['thirst'] -= delta_time * 1
        self.needs['energy'] -= delta_time * 0.05

    def perform_task_based_on_need(self, need_type, search_method, action_method, threshold, regeneration_rate):
        """Généralise la gestion des tâches en fonction des besoins avec gestion d'attente."""
        
        # Vérification de la satisfaction du besoin
        if self.needs[need_type] < threshold and need_type not in self.finding and not getattr(self, f'target_{need_type}'):
            # Démarre la recherche de ressource dans un thread à part
            def search_and_set_target():
                search_method()
                if getattr(self, f'target_{need_type}'):
                    # Une fois la ressource trouvée, créer une tâche pour s'y rendre
                    go_to_task = Task(
                        name=f"Aller à {need_type}",
                        action=self.move_to_target,
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
                
    def is_at_target(self, target, tol=0.1):
        """Vérifie si le PNJ est arrivé à la cible."""
        return self.get_distance_from(*target) < tol

    def perform_tasks(self, delta_time):
        """Effectue les tâches en fonction des besoins."""
        self.perform_task_based_on_need('hunger', self.find_food, 'consume_food', 20, 20 * delta_time)
        self.perform_task_based_on_need('thirst', self.find_water, 'consume_water', 90, 20 * delta_time)
        if self.needs['energy'] < 30:
            self.rest()

    def consume_water(self,delta_time, regeneration_rate):
        """Boit de l'eau pour se réhydrater."""
        self.needs['thirst'] += regeneration_rate
        self.needs['energy'] -= 0.1
        if self.needs['thirst'] >= 100:
            self.target_thirst = None
            self.task_manager.current_task.complete()
            setattr(self, f'target_{self.corresponding_actions["Water"]}', None)

    def consume_food(self,delta_time, regeneration_rate):
        """Mange pour récupérer de la faim."""
        self.needs['hunger'] += regeneration_rate
        if self.needs['hunger'] >= 100:
            self.target_hunger = None

    def search_resource(self, resource_type):
        """Cherche la ressource la plus proche et la cible."""
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

    def find_water(self):
        """Cherche la source d'eau la plus proche."""
        self.search_resource('Water')

    def find_food(self):
        """Cherche la nourriture la plus proche."""
        self.search_resource('Food')

    def set_target(self, target_x, target_y):
        """Définit une cible pour le PNJ et lance le calcul du chemin dans un autre thread."""
        self.target = (target_x, target_y)
        self.path = self.pathfinder.a_star((self.x, self.y), self.target)

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
            
            # if math.isclose(self.x, next_pos[0], abs_tol=0.1) and math.isclose(self.y, next_pos[1], abs_tol=0.1):
            #     print(f"{self} est arrivé à la case {next_pos}.")
            #     last_tile = self.path.pop(0)
            #     if len(self.path) == 0:
            #         self.target = None
            #         self.world.get_tile_at(*last_tile).set_entity_destination(None)
    
    def check_adjacent_tiles_for_resource(self, resource_type):
        """Vérifie si une ressource est présente dans les cases adjacentes au PNJ."""
        adjacent_offsets = [(-1, 0), (1, 0), (0, -1), (0, 1),
                            (-2,0), (2,0), (0,-2), (0,2)]   # Cases adjacentes : droite, gauche, haut, bas
        
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
