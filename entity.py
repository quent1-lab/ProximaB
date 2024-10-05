import random
import pygame
import math
import heapq

class Entity:
    """Classe représentant une entité générique dans le monde."""
    def __init__(self, x, y, world, config, size=1.0, entity_type="generic"):
        self.x = x
        self.y = y
        self.vx = 0  # Vitesse horizontale
        self.vy = 0  # Vitesse verticale (affectée par la gravité)
        self.size = size  # Taille de l'entité
        self.world = world
        self.config = config
        self.entity_type = entity_type  # Type d'entité (PNJ, Animal, Arbre, etc.)
        self.gravity = 9.81  # Gravité (m/s^2)
        self.friction_coefficient = 0.1  # Coefficient de frottement par défaut
        self.on_ground = False  # Indique si l'entité est au sol
        self.in_water = False  # Indique si l'entité est dans l'eau
    
    def apply_gravity(self, delta_time):
        """Applique la gravité si l'entité n'est pas au sol."""
        if not self.on_ground:
            self.vy += self.gravity * delta_time  # Appliquer la gravité

    def apply_friction(self):
        """Applique les frottements pour ralentir l'entité."""
        if self.on_ground:
            self.vx *= (1 - self.friction_coefficient)
            self.vy *= (1 - self.friction_coefficient)
    
    def move(self, delta_time):
        """Déplace l'entité en fonction de sa vitesse et gère les collisions."""
        # Appliquer la gravité
        #self.apply_gravity(delta_time)

        # Calculer la nouvelle position
        new_x = self.x + self.vx * delta_time
        new_y = self.y + self.vy * delta_time

        # Évitement des autres entités
        self.avoid_collision(self.world.entities, delta_time)

        # Vérifier les collisions avec le sol
        self.on_ground = self.collides_with_ground(new_x, new_y)

        # Mise à jour de la position
        self.x = new_x
        self.y = new_y
    
    def collides_with_ground(self, x, y):
        """Vérifie si l'entité entre en collision avec le sol."""
        # Simulation d'une collision avec le sol (à adapter selon ton système de terrain)
        chunk_x = int(x // self.config['chunk_size'])
        chunk_y = int(y // self.config['chunk_size'])
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])

        return chunk.tiles[local_x][local_y] in ['Mountains', 'Plains', 'Beach', 'Solid']

    def avoid_collision(self, entities, delta_time):
        """Évite les collisions avec d'autres entités en ajustant la trajectoire."""
        all_entities = all_entities = [entity for sublist in entities.values() for entity in sublist]
        
        for other_entity in all_entities:
            if other_entity != self:
                # Calculer la distance entre les deux entités
                dx = other_entity.x - self.x
                dy = other_entity.y - self.y
                distance = math.sqrt(dx ** 2 + dy ** 2)

                # Si la distance est inférieure à une certaine limite, éviter la collision
                if distance < self.size * 2:  # On considère la somme des tailles des deux entités
                    # Ajuster les vitesses pour éviter la collision
                    avoidance_factor = 0.1  # Facteur pour ajuster l'évitement
                    self.vx -= dx / distance * avoidance_factor
                    self.vy -= dy / distance * avoidance_factor

    def render(self, screen, scale, screen_x, screen_y):
        """Affiche graphiquement l'entité sur l'écran."""
        # Convertir la position en pixels en fonction de l'échelle
        size_in_pixels = int(self.size * scale)
        
        # Dessiner l'entité (un cercle par défaut) comme une représentation simplifiée
        pygame.draw.circle(screen, (255, 0, 0), (screen_x, screen_y), size_in_pixels // 2)

    def update(self, delta_time):
        """Met à jour l'entité."""
        self.move(delta_time)

    def __str__(self) -> str:
        return f"{self.entity_type} at ({self.x}, {self.y})"

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
        self.tasks = []  # Liste des tâches à accomplir
        self.collaborators = []  # Liste des PNJ avec qui il collabore
        self.target_food = None  # Cible de nourriture
        self.target_water = None  # Cible d'eau
    
    def update(self, delta_time):
        """Mise à jour du PNJ."""
        self.update_needs(delta_time)
        self.perform_tasks(delta_time)
        self.move(delta_time)
    
    def update_needs(self, delta_time):
        """Mise à jour des besoins naturels."""
        self.hunger -= delta_time * 0.1  # Diminution de la faim
        self.thirst -= delta_time * 1  # Diminution de la soif
        self.energy -= delta_time * 0.05  # Diminution de l'énergie
    
    def add_task(self, task):
        """Ajoute une tâche à la liste."""
        self.tasks.append(task)
    
    def perform_tasks(self, delta_time):
        """Effectue les tâches en fonction des besoins."""
        if self.hunger < 20 and not self.target_food:
            print(f'{self} a faim...')
            self.search_food()
        elif self.thirst < 20 and not self.target_water: 
            print(f'{self} a soif...')
            self.search_water()
        elif self.energy < 30:
            print(f'{self} est fatigué...')
            self.rest()
        else:
            if self.tasks:
                current_task = self.tasks[0]
                current_task.perform(self, delta_time)
    
    def search_food(self):
        """Cherche la nourriture la plus proche."""
        closest_food = self.find_closest_resource('Food')  # Recherche la ressource 'Food'
        if closest_food:
            print(f'{self} a trouvé de la nourriture à {closest_food}.')
            self.set_target(closest_food[0], closest_food[1])  # Définir la cible de déplacement
            self.target_food = closest_food
        else:
            print(f'{self} ne trouve pas de nourriture proche.')
          
    def search_water(self):
        """Cherche la source d'eau la plus proche et vise une case adjacente pour y accéder."""
        closest_water = self.find_closest_resource('Water')
        if closest_water:
            adjacent_tile = self.find_adjacent_accessible_tile(closest_water)  # Trouver la case adjacente
            if adjacent_tile:
                print(f'{self} a trouvé de l\'eau et va à une case adjacente à {adjacent_tile}.')
                self.set_target(adjacent_tile[0], adjacent_tile[1])  # Vise la case adjacente
                self.target_water = closest_water
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
        
    def drink(self, delta_time):
        """Boit de l'eau pour récupérer de la soif."""
        print(f'{self} boit...')
        self.thirst += 20  # Régénération de la soif
        self.energy -= delta_time * 0.1  # Coût de l'effort pour boire
        
        if self.thirst >= 100:
            print(f'{self} est hydraté.')
            self.target_water = None
            
    
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

class Animal(Entity):
    """Classe représentant un animal."""
    def __init__(self, x, y, world, config, id, size=1.5, speed=1.2):
        super().__init__(x, y, world, config, size, entity_type="Animal")
        self.speed = speed
        self.id = id

    def wander(self, delta_time):
        """Déplacement aléatoire pour les animaux."""
        direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
        self.vx, self.vy = direction[0] * self.speed, direction[1] * self.speed
        super().move(delta_time)
    
    def update(self, delta_time):
        """Mise à jour de l'animal."""
        self.wander(delta_time)
    
    def generate_random_path(self, num_points, max_distance):
        """Génère un chemin aléatoire avec un nombre de points et une distance maximale."""
        self.path = [(self.x, self.y)]
        for _ in range(num_points):
            last_x, last_y = self.path[-1]
            new_x = last_x + random.uniform(-max_distance, max_distance)
            new_y = last_y + random.uniform(-max_distance, max_distance)
            self.path.append((new_x, new_y))
        self.current_target_index = 0

    def move_along_path(self, delta_time):
        """Déplace l'animal le long du chemin généré."""
        if not self.path:
            return

        target_x, target_y = self.path[self.current_target_index]
        direction_x = target_x - self.x
        direction_y = target_y - self.y
        distance = (direction_x**2 + direction_y**2)**0.5

        if distance < self.speed * delta_time:
            self.x, self.y = target_x, target_y
            self.current_target_index += 1
            if self.current_target_index >= len(self.path):
                self.current_target_index = 0  # Recommence le chemin
        else:
            self.vx = (direction_x / distance) * self.speed
            self.vy = (direction_y / distance) * self.speed
            super().move(delta_time)
    
    def __str__(self) -> str:
        return super().__str__() + f" Animal {self.id}"

class Arbre(Entity):
    """Classe représentant un arbre."""
    def __init__(self, x, y, world, config, id, size=5.0):
        super().__init__(x, y, world, config, size, entity_type="Arbre")
        self.id = id
        
    def render(self, screen, scale, screen_x, screen_y):
        """Affiche graphiquement l'arbre sur l'écran."""
        size_in_pixels = int(self.size * scale)
        
        # Dessiner l'arbre comme un rectangle (tronc)
        pygame.draw.rect(screen, (120,120,36), pygame.Rect(screen_x, screen_y - size_in_pixels, size_in_pixels//2, size_in_pixels))

    def __str__(self) -> str:
        return super().__str__() + f" Arbre {self.id}"

class Aliment(Entity):
    """Classe représentant un aliment."""
    def __init__(self, x, y, world, config, id, size=0.5):
        super().__init__(x, y, world, config, size, entity_type="Aliment")
        self.id = id
    
    def render(self, screen, scale):
        """Affiche graphiquement l'aliment sur l'écran."""
        screen_x = int(self.x * scale)
        screen_y = int(self.y * scale)
        size_in_pixels = int(self.size * scale)
        
        # Dessiner l'aliment comme un petit cercle
        pygame.draw.circle(screen, (0, 255, 0), (screen_x, screen_y), size_in_pixels // 2)
        
    def __str__(self) -> str:
        return super().__str__() + f" Aliment {self.id}"

class Pathfinding:
    """Classe pour gérer le pathfinding avec l'algorithme A*."""
    def __init__(self, world):
        self.world = world

    def heuristic(self, start, goal):
        """Heuristique de la distance de Manhattan (ou Euclidienne) entre deux points."""
        return math.sqrt((goal[0] - start[0]) ** 2 + (goal[1] - start[1]) ** 2)

    def get_neighbors(self, node):
        """Retourne les voisins d'un nœud (les cases adjacentes)."""
        x, y = node
        neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]  # 4 directions de déplacement
        # Filtrer les voisins hors du monde
        return [n for n in neighbors if self.world.is_within_bounds(n[0], n[1])]

    def get_cost(self, node):
        """Retourne le coût de déplacement pour une case donnée (en fonction du type de terrain)."""
        tile_type = self.world.get_tile_at(node[0], node[1])
        if tile_type == 'Water':
            return float('inf')  # Infranchissable sans bateau
        elif tile_type == 'Mountains':
            return 5  # Coût élevé
        elif tile_type == 'Beach':
            return 2
        elif tile_type == 'Plains':
            return 1  # Terrain facile
        return 2  # Coût par défaut

    def a_star(self, start, goal):
        """Implémente l'algorithme A* pour trouver le chemin optimal entre start et goal."""
        open_set = []
        heapq.heappush(open_set, (0, start))  # (F, (x, y))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == goal:
                return self.simplify_path(self.reconstruct_path(came_from, current))

            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + self.get_cost(neighbor)
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        return []  # Pas de chemin trouvé

    def reconstruct_path(self, came_from, current):
        """Reconstitue le chemin à partir du point de départ."""
        total_path = [current]
        while current in came_from:
            current = came_from[current]
            total_path.append(current)
        return total_path[::-1]

    def is_line_passable(self, start, end):
        """Vérifie si un segment de ligne droite entre deux points est franchissable."""
        x1, y1 = start
        x2, y2 = end
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx - dy

        while (x1, y1) != (x2, y2):
            if not self.world.is_within_bounds(x1, y1) or self.get_cost((x1, y1)) == float('inf'):
                return False
            e2 = err * 2
            if e2 > -dy:
                err -= dy
                x1 += sx
            if e2 < dx:
                err += dx
                y1 += sy

        return True

    def simplify_path(self, path):
        """Simplifie le chemin en supprimant les points intermédiaires inutiles."""
        if not path:
            return path

        simplified_path = [path[0]]
        for i in range(2, len(path)):
            if not self.is_line_passable(simplified_path[-1], path[i]):
                simplified_path.append(path[i - 1])
        simplified_path.append(path[-1])

        return simplified_path
