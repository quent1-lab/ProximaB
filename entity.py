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
        self.apply_gravity(delta_time)
        
        # Calculer la nouvelle position
        new_x = self.x + self.vx * delta_time
        new_y = self.y + self.vy * delta_time
        
        # Vérifier les collisions avec le sol
        self.on_ground = self.collides_with_ground(new_x, new_y)
        
        self.x = new_x
        self.y = new_y

    def collides_with_ground(self, x, y):
        """Vérifie si l'entité entre en collision avec le sol."""
        chunk_x = int(x // self.config['chunk_size'])
        chunk_y = int(y // self.config['chunk_size'])
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])
        
        # Si la tuile est une montagne ou un autre biome solide, il y a collision
        return chunk.tiles[local_x][local_y] in ['Mountains', 'Plains', 'Beach', 'Solid']

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
        pygame.draw.rect(screen, (0, 100, 0), pygame.Rect(screen_x, screen_y - size_in_pixels, size_in_pixels//2, size_in_pixels))

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
                return self.reconstruct_path(came_from, current)

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
