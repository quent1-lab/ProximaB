from entity import Entity, Pathfinding
from task import Task, TaskManager
import math

class PNJ(Entity):
    """Classe représentant un PNJ."""
    def __init__(self, x, y, world, config, id, size=1.75, speed=1.0):
        super().__init__(x, y, world, config, size, entity_type="PNJ")
        self.id = id
        self.speed = speed
        self.target = None
        self.pathfinder = Pathfinding(world)
        self.path = []
        self.hunger = 100  # Niveau de faim (0 = mort de faim, 100 = rassasié)
        self.thirst = 100  # Niveau de soif (0 = mort de soif, 100 = hydraté)
        self.energy = 100  # Niveau d'énergie (0 = endormi, 100 = pleine forme)
        self.collaborators = []  # Liste des PNJ avec qui il collabore
        self.target_food = None  # Cible de nourriture
        self.target_water = None  # Cible d'eau
        
        self.task_manager = TaskManager(self)
    
    def update(self, delta_time):
        """Met à jour l'état de l'entité et exécute les tâches."""
        self.update_needs(delta_time)
        self.perform_tasks(delta_time)
        self.task_manager.execute_tasks(delta_time)
        self.move(delta_time)
    
    def update_needs(self, delta_time):
        """Mise à jour des besoins naturels."""
        self.hunger -= delta_time * 0.1  # Diminution de la faim
        self.thirst -= delta_time * 1  # Diminution de la soif
        self.energy -= delta_time * 0.05  # Diminution de l'énergie
    
    def perform_tasks(self, delta_time):
        """Effectue les tâches en fonction des besoins."""
        if self.hunger < 20 and not self.target_food:
            print(f'{self} a faim...')
            self.search_food()
        elif self.thirst < 90 and not self.target_water: 
            print(f'{self} a soif...')
            self.search_water()
        elif self.energy < 30:
            print(f'{self} est fatigué...')
            self.rest()
    
    def search_water(self):
        """Recherche de l'eau et création des tâches liées."""
        # 1. Créer une tâche pour se rendre à côté de l'eau
        go_to_water_task = Task(
            name="Aller à l'eau",
            action=self.go_to_water,  # Action d'aller à l'eau
            priority=100,  # Priorité élevée pour la soif
            energy_cost=2  # Consomme de l'énergie
        )

        # 2. Créer une tâche pour boire
        drink_task = Task(
            name="Boire de l'eau",
            action=self.drink_water,  # Action de boire
            priority=100,  # Priorité élevée
            energy_cost=1  # Coût énergétique
        )

        # Lier les tâches ensemble
        self.task_manager.create_linked_tasks([go_to_water_task, drink_task])

    def go_to_water(self, pnj, delta_time):
        """Action pour aller à l'eau."""
        if not self.target_water:
            self.find_water()  # Recherche de l'eau
        else:
            if math.isclose(self.x, self.target_water[0], abs_tol=0.2) and math.isclose(self.y, self.target_water[1], abs_tol=0.2):
                self.task_manager.current_task.complete()  # Marquer la tâche comme complétée

    def drink_water(self, pnj, delta_time):
        """Action pour boire de l'eau."""
        print(f"{pnj} boit de l'eau.")
        self.thirst += 20 * delta_time  # Régénération de la soif
        self.energy -= delta_time * 0.1  # Coût de l'effort pour boire
        
        if self.thirst >= 100:
            print(f'{self} est hydraté.')
            self.target_water = None
            self.task_manager.current_task.complete()  # Marquer la tâche comme complétée

    def search_food(self):
        """Cherche la nourriture la plus proche."""
        closest_food = self.find_closest_resource('Food')  # Recherche la ressource 'Food'
        if closest_food:
            print(f'{self} a trouvé de la nourriture à {closest_food}.')
            self.set_target(closest_food[0], closest_food[1])  # Définir la cible de déplacement
            self.target_food = closest_food
        else:
            print(f'{self} ne trouve pas de nourriture proche.')
          
    def find_water(self):
        """Cherche la source d'eau la plus proche et vise une case adjacente pour y accéder."""
        closest_water = self.find_closest_resource('Water')
        if closest_water:
            adjacent_tile = self.find_adjacent_accessible_tile(closest_water)  # Trouver la case adjacente
            if adjacent_tile:
                print(f'{self} a trouvé de l\'eau et va à une case adjacente à {adjacent_tile}.')
                self.set_target(adjacent_tile[0], adjacent_tile[1])  # Vise la case adjacente
                self.target_water = adjacent_tile
            else:
                print(f'{self} a trouvé de l\'eau, mais aucune case adjacente n\'est accessible.')
        else:
            print(f'{self} ne trouve pas d\'eau proche.')

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
        return tile != 'Water' and tile != 'Obstacle'  # Exemple: doit être ni eau ni un obstacle
    
    def eat(self):
        """Mange de la nourriture pour récupérer de la faim."""
        print(f'{self} mange...')
        self.hunger += 20  # Régénération de la faim
            
    def rest(self):
        """Récupère de l'énergie en se reposant."""
        print(f'{self} se repose...')
        self.energy += 10  # Régénération de l'énergie
    
    def consume_resource(self, resource_type):
        """Consomme la ressource (nourriture ou eau) une fois atteinte."""
        if resource_type == 'Food' and self.target_food:
            if math.isclose(self.x, self.target_food[0], abs_tol=0.5) and math.isclose(self.y, self.target_food[1], abs_tol=0.5):
                print(f'{self} consomme la nourriture à {self.target_food}.')
                self.hunger = min(self.hunger + 50, 100)  # Régénère la faim
                self.target_food = None  # La nourriture a été consommée
        elif resource_type == 'Water' and self.target_water:
            if math.isclose(self.x, self.target_water[0], abs_tol=0.5) and math.isclose(self.y, self.target_water[1], abs_tol=0.5):
                print(f'{self} boit de l\'eau à {self.target_water}.')
                self.thirst = min(self.thirst + 50, 100)  # Régénère la soif
                self.target_water = None  # L'eau a été consommée
    
    def collaborate(self, other_pnj):
        """Collabore avec un autre PNJ."""
        if other_pnj not in self.collaborators:
            self.collaborators.append(other_pnj)
            print(f'{self} collabore avec {other_pnj}.')
            # Partager des tâches ou des ressources
    
    def find_closest_resource(self, resource_type):
        """Trouve la ressource la plus proche de type spécifié (Food, Water, etc.)."""
        closest_resource = None
        closest_distance = float('inf')
        
        # Parcourir les chunks voisins pour trouver des ressources
        for chunk in self.world.get_chunks_around(self.x, self.y, radius=5):  # Rayon de recherche
            for x, y, tile in chunk.get_tiles():
                if tile == resource_type:
                    distance = self.get_distance_from(x, y)
                    if distance < closest_distance:
                        closest_resource = (x, y)
                        closest_distance = distance
        
        return closest_resource

    def get_distance_from(self, x, y):
        """Calcule la distance entre le PNJ et une position donnée."""
        return math.sqrt((self.x - x) ** 2 + (self.y - y) ** 2)

    def set_target(self, target_x, target_y):
        """Définit une cible pour le PNJ et calcule le chemin."""
        self.target = (target_x, target_y)
        self.path = self.pathfinder.a_star((self.x, self.y), self.target)

    def move(self, delta_time):
        """Déplace le PNJ vers la cible."""
        if self.path:
            next_pos = self.path[0]
            dx = next_pos[0] - self.x
            dy = next_pos[1] - self.y
            distance = math.sqrt(dx ** 2 + dy ** 2)
            if distance > 0:
                # Déplacement en fonction de la vitesse
                self.vx = (dx / distance) * self.speed
                self.vy = (dy / distance) * self.speed
                super().move(delta_time)
            
            if math.isclose(self.x, next_pos[0], abs_tol=0.1) and math.isclose(self.y, next_pos[1], abs_tol=0.1):
                self.path.pop(0)
    
    def __str__(self) -> str:
        return super().__str__() + f" PNJ {self.id}"