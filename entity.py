import random, pygame, math, heapq

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

        # Appliquer les frottements
        self.apply_friction()

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

    def render(self, screen, scale, screen_x, screen_y, color=(255, 0, 0), shape='circle', **kwargs):
        """Affiche graphiquement l'entité sur l'écran avec des options de personnalisation."""
        # Convertir la position en pixels en fonction de l'échelle
        size_in_pixels = int(self.size * scale)

        # Dessiner l'entité en fonction de la forme spécifiée
        if shape == 'circle':
            pygame.draw.circle(screen, color, (screen_x, screen_y), size_in_pixels // 2)
        elif shape == 'square':
            pygame.draw.rect(screen, color, (screen_x - size_in_pixels // 2, screen_y - size_in_pixels // 2, size_in_pixels, size_in_pixels))
        # Ajouter d'autres formes si nécessaire
        else:
            raise ValueError(f"Forme non supportée: {shape}")

    def update(self, delta_time):
        """Met à jour l'entité."""
        self.move(delta_time)

    def has_moved(self):
        """Retourne True si l'entité a bougé, False sinon."""
        return self.vx != 0 or self.vy != 0
    
    def __str__(self) -> str:
        return f"{self.entity_type} at ({self.x:.1f}, {self.y:.1f})"

class Animal(Entity):
    def __init__(self, name, x, y, world, energy=100, hunger=100, thirst=100):
        super().__init__(x, y, world, world.config, entity_type="animal")
        self.name = name
        self.is_alive = True
        self.speed = 1.0  # Vitesse de déplacement de base
        self.intelligence = 0.5  # Niveau d'intelligence de l'animal (peut influencer ses décisions)
        self.direction = (random.uniform(-1, 1), random.uniform(-1, 1))
        self.normalize_direction()

    def normalize_direction(self):
        """Normalise le vecteur de direction."""
        length = math.sqrt(self.direction[0] ** 2 + self.direction[1] ** 2)
        if length > 0:
            self.direction = (self.direction[0] / length, self.direction[1] / length)

    def wander(self, delta_time):
        """Déplacement aléatoire pour les animaux avec des mouvements plus réalistes."""
        change = (random.uniform(-0.1, 0.1), random.uniform(-0.1, 0.1))
        self.direction = (self.direction[0] + change[0], self.direction[1] + change[1])
        self.normalize_direction()
        self.vx, self.vy = self.direction[0] * self.speed, self.direction[1] * self.speed
        self.vx = float(self.vx)
        self.vy = float(self.vy)
        super().move(delta_time)
        
    def move(self):
        """Logique de déplacement de l'animal."""
        # Par exemple, recherche de nourriture ou d'eau si l'animal a faim ou soif
        if self.hunger > 70:
            self.search_for_food()
        elif self.thirst > 70:
            self.search_for_water()
        else:
            self.wander()

    def search_for_food(self):
        """Méthode de recherche de nourriture."""
        # Logique de pathfinding pour trouver un fruit ou une autre source de nourriture
        pass

    def search_for_water(self):
        """Méthode de recherche d'eau."""
        # Utilise le pathfinding pour trouver une source d'eau
        pass

    def eat(self, food):
        """L'animal mange la nourriture trouvée."""
        food.consume(self)

    def drink(self, water_tile):
        """L'animal boit de l'eau."""
        self.thirst -= 20  # Réduit la soif de l'animal

    def die(self):
        """L'animal meurt."""
        self.is_alive = False
        # Logique pour enlever l'animal du monde
        pass
    
    def react_to_pnj(self, pnj):
        """Réaction de l'animal en fonction de la proximité avec un PNJ."""
        distance = self.calculate_distance(pnj)
        if distance < 5 and self.intelligence > 0.3:
            self.run_away_from(pnj)  # L'animal fuit si le PNJ est trop proche
        elif distance < 2:
            self.attack(pnj)  # L'animal attaque s'il est carnivore et que le PNJ est trop proche

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
    
    def update(self, delta_time):
        """Mise à jour de l'animal."""
        self.wander(delta_time)
        
    def render(self, screen, scale, screen_x, screen_y):
        return super().render(screen, scale, screen_x, screen_y, color=(0, 255, 0), shape='square')
    
    def __str__(self) -> str:
        return super().__str__() + f" Animal {self.id}"

class Food(Entity):
    def __init__(self, name, nutrition_value, x, y, world):
        super().__init__(x, y,world, world.config,size=0.5,entity_type="food")
        self.name = name
        self.nutrition_value = nutrition_value  # Valeur nutritive
        self.is_consumed = False  # Indique si la nourriture a été consommée
        
    def consume(self, entity):
        """Méthode appelée lorsqu'un PNJ consomme cette nourriture."""
        entity.hunger -= self.nutrition_value
        # Supprimer la nourriture après consommation
        self.remove_from_world()

    def remove_from_world(self):
        # Logique pour enlever l'élément du monde
        pass
    
    def update(self, delta_time):
        pass
    
    def render(self, screen, scale, screen_x, screen_y):
        return super().render(screen, scale, screen_x, screen_y, color=(100, 20, 50), shape='circle')
    
    def __str__(self) -> str:
        return f"{self.name} at ({self.x:.1f}, {self.y:.1f})"

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
        tile_type = self.world.get_tile_at(node[0], node[1]).biome
        
        if tile_type == 'Water':
            return float('inf')  # Infranchissable sans bateau
        elif tile_type == 'Mountains':
            return 5  # Coût élevé
        elif tile_type == 'Beach':
            return 2
        elif tile_type == 'Plains':
            return 1  # Terrain facile
        return 2  # Coût par défaut

    def a_star(self, start, goal, max_iterations=1000, *args):
        """Implémente l'algorithme A* pour trouver le chemin optimal entre start et goal."""
        open_set = []
        heapq.heappush(open_set, (0, start))  # (F, (x, y))
        came_from = {}
        g_score = {start: 0}
        f_score = {start: self.heuristic(start, goal)}
        callback_set_path = args[0] if args else None
        path_found = False  # Variable de contrôle pour indiquer que le chemin a été trouvé
        iterations = 0  # Compteur d'itérations

        while open_set and iterations < max_iterations:
            iterations += 1
            _, current = heapq.heappop(open_set)
            if current == goal:
                path = self.simplify_path(self.reconstruct_path(came_from, current))
                if path[0] == start:
                    path.pop(0)  # Enlève le point de départ
                if callback_set_path:
                    callback_set_path(path)
                path_found = True  # Indique que le chemin a été trouvé
                break  # Sort de la boucle
                        
            for neighbor in self.get_neighbors(current):
                tentative_g_score = g_score[current] + self.get_cost(neighbor)
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self.heuristic(neighbor, goal)
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))

        if path_found:
            return path
        else:
            return []  # Retourne une liste vide si aucun chemin n'a été trouvé

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
        
        # Modifie l'arrivée pour atterir au milieu de la case finale
        if len(simplified_path) > 1:
            last_node = simplified_path[-1]
            simplified_path[-1] = (last_node[0] + 0.5, last_node[1] + 0.5)

        return simplified_path
