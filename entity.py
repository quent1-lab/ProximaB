import random
import pygame
import heapq
import math

class Entity:
    """Classe représentant une entité physique avec des règles de physique."""
    def __init__(self, x, y, world, config):
        self.x = x
        self.y = y
        self.offset_x = 0
        self.offset_y = 0
        self.vx = 1  # Vitesse horizontale
        self.vy = 1  # Vitesse verticale (affectée par la gravité)
        self.world = world
        self.config = config
        self.gravity = 9.81  # Gravité (m/s^2)
        self.on_ground = False  # Indique si l'entité est au sol

    def apply_gravity(self, delta_time):
        """Applique la gravité si l'entité n'est pas au sol."""
        if not self.on_ground:
            self.vy += self.gravity * delta_time  # Appliquer la gravité
        else:
            self.vy = 0  # Si l'entité est au sol, elle ne tombe plus

    def move(self, delta_time):
        """Déplace l'entité en fonction de sa vitesse et gère les collisions."""
        #self.apply_gravity(delta_time)
        
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

    def get_ground_level(self, x, y):
        """Retourne la position Y du sol le plus proche sous l'entité."""
        chunk_x = int(x // self.config['chunk_size'])
        chunk_y = int(y // self.config['chunk_size'])
        chunk = self.world.get_chunk(chunk_x, chunk_y)
        local_x = int(x % self.config['chunk_size'])
        local_y = int(y % self.config['chunk_size'])
        for local_y in range(local_y, -1, -1):
            if chunk.tiles[local_x][local_y] in ['Mountains', 'Plains', 'Beach', 'Solid']:
                return local_y
        return y  # Si aucune collision détectée, on ne change pas la position Y

class PNJ(Entity):
    """Classe représentant un PNJ avec des interactions et des règles de physique."""
    def __init__(self, x, y, world, config, size=1.75, speed=1.0):
        super().__init__(x, y, world, config)
        self.interaction_radius = 5  # Rayon d'interaction entre les PNJ
        self.friction_coefficient = 0.1  # Coefficient de frottement (ex: surface glissante ou rugueuse)
        self.bounce_factor = 0.5  # Facteur de rebond (1 = rebond parfait, 0 = aucun rebond)
        self.size = size  # Taille du PNJ en mètres (par exemple, 1.75 m)
        self.speed = speed  # Vitesse du PNJ (unités par seconde)
        self.in_water = False
        self.path = []  # Le chemin optimal calculé
        self.target = None  # La cible du PNJ
        self.pathfinder = Pathfinding(world)

    def set_target(self, target_x, target_y):
        """Définit une cible pour le PNJ et calcule le chemin optimal."""
        self.target = (target_x, target_y)
        self.path = self.pathfinder.a_star((self.x, self.y), self.target)

    def move(self, delta_time):
        """Déplace le PNJ le long du chemin calculé par l'algorithme A*."""
        if self.path:
            next_pos = self.path[0]
            dx = next_pos[0] - self.x
            dy = next_pos[1] - self.y
            distance = math.sqrt(dx ** 2 + dy ** 2)
            if distance > 0:
                # Déplacement en fonction de la vitesse du PNJ
                self.vx = (dx / distance) * self.speed
                self.vy = (dy / distance) * self.speed
                super().move(delta_time)
            
            # Si le PNJ atteint la prochaine case, on la retire du chemin
            if math.isclose(self.x, next_pos[0], abs_tol=0.1) and math.isclose(self.y, next_pos[1], abs_tol=0.1):
                self.path.pop(0)

    def can_traverse(self, tile_type):
        """Vérifie si le PNJ peut traverser un type de terrain."""
        if tile_type == 'Water' and not self.in_boat():
            return False
        return True

    def in_boat(self):
        """Vérifie si le PNJ dispose d'un moyen de transport aquatique."""
        # Ici on peut ajouter la logique pour gérer si le PNJ possède un bateau
        return self.in_water and self.has_boat()

    def apply_friction(self):
        """Applique les frottements pour ralentir le PNJ."""
        if self.on_ground:
            self.vx *= (1 - self.friction_coefficient)
            self.vy *= (1 - self.friction_coefficient)

    def interact_with_other_pnj(self, pnj_list):
        """Interagit avec d'autres PNJ dans le rayon d'interaction."""
        for other_pnj in pnj_list:
            if other_pnj != self:
                distance = self.get_distance(other_pnj)
                if distance < self.interaction_radius:
                    self.avoid_collision(other_pnj)
                    # Exemples d'autres interactions : se suivre, échanger des infos, etc.
    
    def get_distance(self, other_pnj):
        """Calcule la distance entre deux PNJ."""
        return ((self.x - other_pnj.x)**2 + (self.y - other_pnj.y)**2)**0.5

    def avoid_collision(self, other_pnj):
        """Évite les collisions avec un autre PNJ en ajustant la vitesse."""
        dx = self.x - other_pnj.x
        dy = self.y - other_pnj.y
        distance = self.get_distance(other_pnj)
        if distance > 0:
            # Ajuster la vitesse pour éviter la collision
            self.vx += dx / distance * 0.1
            self.vy += dy / distance * 0.1

    def handle_collision(self, delta_time):
        """Gère les collisions avec le terrain ou les PNJ."""
        if self.collides_with_ground(self.x, self.y):
            self.vy = -self.vy * self.bounce_factor  # Rebond vertical
            self.on_ground = True
        else:
            self.on_ground = False
        
        # Déplacement en tenant compte des frottements et des collisions
        self.apply_friction()
        self.move(delta_time)
    
    def apply_friction(self):
        """Applique les frottements pour ralentir le PNJ en fonction du type de terrain."""
        current_tile = self.world.get_tile_at(self.x, self.y)
        if current_tile == 'Water':
            self.vx *= 0.5  # Frottement élevé dans l'eau
            self.vy *= 0.5
        elif current_tile == 'Mountains':
            self.vx *= 0.8  # Déplacement plus lent dans les montagnes
            self.vy *= 0.8
        else:
            self.vx *= (1 - self.friction_coefficient)
            self.vy *= (1 - self.friction_coefficient)
    
    def render(self, screen, scale):
        """Affiche graphiquement le PNJ sur l'écran."""
        # Convertir la position en pixels en fonction de l'échelle
        screen_x = int(self.x * scale)
        screen_y = int(self.y * scale)
        size_in_pixels = int(self.size * scale)
        
        # Dessiner le PNJ comme un rectangle pour simplifier
        pygame.draw.rect(screen, (0, 255, 0), pygame.Rect(screen_x, screen_y - size_in_pixels, size_in_pixels//2, size_in_pixels))


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
