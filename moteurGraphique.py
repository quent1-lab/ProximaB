import json, pygame, uuid, perlin_noise, numpy as np
from chunk_ import Chunk

# Charger la configuration depuis un fichier JSON
def load_config(file_path):
    with open(file_path, 'r') as f:
        config = json.load(f)
    return config

# ======================================================================================
# =============================== Class PerlinNoise ====================================
# ======================================================================================

class PerlinNoiseGenerator:
    """Classe pour générer du bruit de Perlin."""
    def __init__(self, config):
        self.noise = perlin_noise.PerlinNoise(octaves=config['perlin']['octaves'], seed=config['perlin']['seed'])
    
    def get_noise(self, x, y, chunk_size):
        """Retourne la valeur du bruit de Perlin pour des coordonnées données."""
        nx = x / chunk_size
        ny = y / chunk_size
        return self.noise([nx, ny])

# ======================================================================================
# ================================= Class WORLD ========================================
# ======================================================================================


class World:
    """Classe gérant le monde et les chunks générés."""
    def __init__(self, config, **kwargs):
        self.noise_generator = PerlinNoiseGenerator(config)
        self.loaded_chunks = {}  # Dictionnaire stockant les chunks chargés
        self.tiles_with_entities = []  # Liste des tuiles ayant des entités
        self.config = config
        self.entities = {}  # Dict des entités dans le monde
        self.visible_chunks = set()  # Suivi des chunks actuellement visibles
        self.recent_chunks = {}  # Suivi des chunks récemment visibles
        self.chunk_cache_duration = config.get('chunk_cache_duration', 10)  # Durée de vie des chunks récents (par défaut 10 cycles)
        
        self.__dict__.update(kwargs)
        self.chunk_lock = self.__dict__.get("chunk_lock", None)
        self.entity_lock = self.__dict__.get("entity_lock", None)
        
    def unload_chunks_outside_view(self, left_bound, right_bound, top_bound, bottom_bound):
        """Décharge les chunks qui sont hors de la zone visible de la caméra après un délai."""
        chunk_size = self.config['chunk_size']
        
        # Déterminer les coordonnées des chunks dans les limites visibles
        left_chunk = int(left_bound) // chunk_size
        right_chunk = int(right_bound) // chunk_size
        top_chunk = int(top_bound) // chunk_size
        bottom_chunk = int(bottom_bound) // chunk_size
        
        # Créer un set pour les nouveaux chunks visibles
        new_visible_chunks = set()
        for chunk_x in range(left_chunk, right_chunk + 1):
            for chunk_y in range(top_chunk, bottom_chunk + 1):
                new_visible_chunks.add((chunk_x, chunk_y))
        
        # Marquer les chunks récemment visibles et décharger ceux dont le compteur atteint 0
        chunks_to_unload = []
        for chunk_coords in self.recent_chunks.copy():
            if chunk_coords not in new_visible_chunks:
                self.recent_chunks[chunk_coords] -= 1  # Décrémenter le compteur
                if self.recent_chunks[chunk_coords] <= 0:
                    chunks_to_unload.append(chunk_coords)  # Le chunk sera déchargé
            else:
                del self.recent_chunks[chunk_coords]  # Retirer du cache si visible à nouveau
        
        # Ajouter les nouveaux chunks visibles au cache
        self.visible_chunks = new_visible_chunks
        for chunk_coords in self.visible_chunks:
            if chunk_coords in self.loaded_chunks and chunk_coords not in self.recent_chunks:
                self.recent_chunks[chunk_coords] = self.chunk_cache_duration
        
        # Décharger les chunks qui sont restés hors de la vue trop longtemps
        for chunk_coords in chunks_to_unload:
            if chunk_coords in self.loaded_chunks:
                del self.loaded_chunks[chunk_coords]  # Décharger le chunk
    
    def get_tile_at(self, x, y):
        """Retourne le type de terrain pour les coordonnées globales (x, y)."""
        chunk_x = int(x) // self.config['chunk_size']
        chunk_y = int(y) // self.config['chunk_size']
        chunk = self.get_chunk(chunk_x, chunk_y)
        
        # Calculer les coordonnées locales dans le chunk
        local_x = int(x) % self.config['chunk_size']
        local_y = int(y) % self.config['chunk_size']
        return chunk.tiles[local_x][local_y]
    
    def add_entity(self, entity):
        """Ajoute une entité au monde."""
        if entity.entity_type not in self.entities:
            self.entities[entity.entity_type] = []
        self.entities[entity.entity_type].append(entity)
    
    def remove_entity(self, entity_id):
        """Supprime une entité du monde."""
        for entity_type, entity_list in self.entities.items():
            for i, entity in enumerate(entity_list):
                if entity.id == entity_id:
                    del entity_list[i]
    
    def generate_id(self):
        """Génère un ID unique pour une entité."""
        return str(uuid.uuid1())
    
    def update_entities(self, delta_time):
        """Met à jour toutes les entités du monde."""
        for entity_type, entity_list in self.entities.items():
            self.tiles_with_entities = []  # Liste des tuiles ayant des entités
            for entity in entity_list:
                entity.update(delta_time)
        
        # Vérifier la présence des entités sur les tuiles
        self.entity_is_present()
        
        # Vérifier la présence des entités sur les tuiles
        self.entity_is_not_present()
   
    def search_for_entities(self, x, y, radius, entity_type):
        """Recherche des entités dans un rayon donné autour des coordonnées (x, y)."""
        entities_in_radius = []
        for entity in self.entities[entity_type]:
            distance = np.sqrt((entity.x - x) ** 2 + (entity.y - y) ** 2)
            if distance <= radius:
                entities_in_radius.append(entity)
        return entities_in_radius
    
    def get_closest_entity(self, x, y, entity_type):
        """Retourne l'entité la plus proche des coordonnées (x, y)."""
        closest_entity = None
        closest_distance = np.inf
        for entity in self.entities[entity_type]:
            distance = np.sqrt((entity.x - x) ** 2 + (entity.y - y) ** 2)
            if distance < closest_distance:
                closest_entity = entity
                closest_distance = distance
        return closest_entity

    def get_chunk(self, chunk_x, chunk_y):
        """Retourne un chunk, le génère si nécessaire."""
        if (chunk_x, chunk_y) not in self.loaded_chunks:
            # Générer et stocker le chunk s'il n'existe pas encore
            self.loaded_chunks[(chunk_x, chunk_y)] = Chunk(chunk_x * self.config['chunk_size'], chunk_y * self.config['chunk_size'], self.noise_generator, self.config, chunk_lock=self.chunk_lock, entity_lock=self.entity_lock)
            # Ajouter un log pour enregistrer l'appel
            # print(f"Chunk généré pour ({chunk_x}, {chunk_y})")
            # print("Appelé par :")
            # traceback.print_stack(limit=5)  # Limite la profondeur de la pile d'appels affichée
        return self.loaded_chunks[(chunk_x, chunk_y)]
    
    def get_chunks_around(self,x,y,radius):
        """Retourne les chunks autour des coordonnées (x, y) dans un rayon donné."""
        chunk_size = self.config['chunk_size']
        chunk_x = int(x) // chunk_size
        chunk_y = int(y) // chunk_size
        chunks = []
        for i in range(-radius, radius + 1):
            for j in range(-radius, radius + 1):
                chunks.append(self.get_chunk(chunk_x + i, chunk_y + j))
        return chunks     
    
    def load_chunks_around_camera(self, left_bound, right_bound, top_bound, bottom_bound):
        """Charge les chunks dans la zone définie par les limites visibles de la caméra."""
        chunk_size = self.config['chunk_size']

        # Déterminer les coordonnées des chunks à charger
        left_chunk = int(left_bound) // chunk_size
        right_chunk = int(right_bound) // chunk_size
        top_chunk = int(top_bound) // chunk_size
        bottom_chunk = int(bottom_bound) // chunk_size

        # Charger tous les chunks dans la zone visible
        for chunk_x in range(left_chunk, right_chunk + 1):
            for chunk_y in range(top_chunk, bottom_chunk + 1):
                self.get_chunk(chunk_x, chunk_y)
    
    def is_within_bounds(self, x, y):
        """Vérifie si les coordonnées (x, y) sont dans les limites du monde généré."""
        # Si le monde est théoriquement infini (généré à la demande), tout est dans les limites
        return True  # On considère que les coordonnées sont toujours valides

    def entity_is_present(self):
        """Vérifie si une entité est présente sur une tuile, et met à jour la tuile en conséquence."""
        for entity_type, entity_list in self.entities.items():
            for entity in entity_list:
                tile = self.get_tile_at(entity.x, entity.y)
                self.add_entity_to_tile(tile)
        
    def entity_is_not_present(self):
        """Met à jour la présence d'une entité sur les tuiles spécifiques où une entité était présente."""
        # Parcourir seulement les tuiles ayant des entités
        for tile in self.tiles_with_entities[:]:  # [:] pour éviter la modification de la liste pendant l'itération
            if tile.has_entity:
                # Mettre à jour la présence de l'entité
                tile.set_entity_presence(False)
                # Retirer la tuile de la liste une fois l'entité disparue
                self.tiles_with_entities.remove(tile)

    def add_entity_to_tile(self, tile):
        """Ajoute une entité à une tuile et l'enregistre dans la liste."""
        tile.set_entity_presence(True)
        if tile not in self.tiles_with_entities:
            self.tiles_with_entities.append(tile)

    def remove_entity_from_tile(self, tile):
        """Retire une entité d'une tuile."""
        tile.set_entity_presence(False)
        if tile in self.tiles_with_entities:
            self.tiles_with_entities.remove(tile)

# ======================================================================================
# ================================= Class CAMERA =======================================
# ======================================================================================

class Camera:
    """Classe gérant la caméra comme entité invisible et fixe, les chunks se déplacent autour d'elle."""
    def __init__(self, world, config, mode="free", start_x=0, start_y=0):
        self.world = world
        self.x = start_x
        self.y = start_y
        self.world_offset_x = 0
        self.world_offset_y = 0
        self.mode = mode
        self.config = config
        self.target_pnj = None  # PNJ à suivre
        self.screen_width = config['screen_width']
        self.screen_height = config['screen_height']
        self.camera_center_x = self.screen_width // 2  # Caméra centrée horizontalement
        self.camera_center_y = self.screen_height // 2  # Caméra centrée verticalement
        self.scale = config['scale']  # Échelle initiale (zoom de base)
        self.zoom_speed = 0.5  # Vitesse de zoom
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

    def set_mode(self, mode, target_pnj=None):
        """Définit le mode de la caméra (fixe, libre ou suivi d'un PNJ)."""
        self.mode = mode
        if mode == "follow":
            self.target_pnj = target_pnj

    def update(self, delta_time):
        """Met à jour le zoom dynamique et le déplacement des chunks pour donner l'effet de mouvement."""
        self.handle_zoom()

        if self.mode == "free":
            # Les chunks se déplacent en fonction des touches pressées
            dx, dy = 0, 0
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT] or keys[pygame.K_q]:
                dx = -1.0 * self.config['camera_speed'] * delta_time
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1.0 * self.config['camera_speed'] * delta_time
            if keys[pygame.K_UP] or keys[pygame.K_z]:
                dy = -1.0 * self.config['camera_speed'] * delta_time
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1.0 * self.config['camera_speed'] * delta_time
            self.move(dx, dy)    
        elif self.mode == "follow" and self.target_pnj:
            # Suivre la position du PNJ
            self.world_offset_x = self.target_pnj.x - self.camera_center_x / self.scale
            self.world_offset_y = self.target_pnj.y - self.camera_center_y / self.scale

        # Toujours s'assurer que les chunks sont chargés après mise à jour de la caméra
        self.update_chunks()

    def move(self, dx, dy):
        """Déplace le monde en fonction du déplacement de la caméra."""
        self.world_offset_x += dx / self.scale
        self.world_offset_y += dy / self.scale
        self.update_chunks()

    def update_chunks(self):
        """Charge et décharge les chunks autour de la position actuelle de la caméra."""
        camera_world_x = self.camera_center_x / self.scale + self.world_offset_x
        camera_world_y = self.camera_center_y / self.scale + self.world_offset_y
        
        # Calculer la taille du chunk en termes de distance dans le monde
        chunk_size_in_world = self.config['chunk_size']
        
        # Calculer les limites visibles de la caméra en termes de coordonnées du monde
        left_bound = camera_world_x - (self.screen_width / 2) / self.scale
        right_bound = camera_world_x + (self.screen_width / 2) / self.scale
        top_bound = camera_world_y - (self.screen_height / 2) / self.scale
        bottom_bound = camera_world_y + (self.screen_height / 2) / self.scale

        # Charger les nouveaux chunks et décharger ceux qui ne sont plus visibles
        self.world.load_chunks_around_camera(left_bound, right_bound, top_bound, bottom_bound)
        self.world.unload_chunks_outside_view(left_bound, right_bound, top_bound, bottom_bound)

    def handle_zoom(self):
        """Gère le zoom dynamique avec la molette de la souris."""
        zoom_in = pygame.mouse.get_pressed()[0]  # Bouton gauche pour zoom avant
        zoom_out = pygame.mouse.get_pressed()[2]  # Bouton droit pour zoom arrière
        
        if zoom_in:
            self.scale += self.zoom_speed
        if zoom_out and self.scale > self.zoom_speed:  # Empêcher un zoom trop petit
            self.scale -= self.zoom_speed

    def render(self):
        """Affiche le monde et les PNJ avec déplacement du décor en fonction de la caméra."""
        self.screen.fill((135, 206, 235))  # Fond bleu ciel

        # Afficher les chunks
        for chunk in list(self.world.loaded_chunks.values()):
            self.render_chunk(chunk)

        # Afficher les PNJ
        for entity_list in self.world.entities.values():
            for entity in entity_list:
                screen_x = int((entity.x - self.world_offset_x) * self.scale)
                screen_y = int((entity.y - self.world_offset_y) * self.scale)
                entity.render(self.screen, self.scale, screen_x, screen_y)
        
        # Dessiner le chemin du PNJ
        for pnj in self.world.entities['PNJ']:
            for i in range(len(pnj.path)):
                if i == 0:
                    start_x, start_y = pnj.x, pnj.y
                else:
                    start_x, start_y = pnj.path[i - 1]
                end_x, end_y = pnj.path[i]
                pygame.draw.line(self.screen, (255, 0, 0), 
                                 ((start_x - self.world_offset_x) * self.scale, (start_y - self.world_offset_y) * self.scale),
                                 ((end_x - self.world_offset_x) * self.scale, (end_y - self.world_offset_y) * self.scale))
        
        # Ecriture du nombre de chunks chargés
        font = pygame.font.Font(None, 24)
        text = font.render(f"Chunks loaded: {len(self.world.loaded_chunks)}", True, (255, 255, 255))
        self.screen.blit(text, (10, 40))

    def render_chunk(self, chunk, *args):
        """Affiche un chunk avec déplacement en fonction de la caméra."""
        
        draw_chunk = args[0] if args else False            
        
        for x in range(chunk.chunk_size):
            for y in range(chunk.chunk_size):
                tile_type = chunk.tiles[x][y].biome
                screen_x = int((chunk.x_offset + x - self.world_offset_x) * self.scale)
                screen_y = int((chunk.y_offset + y - self.world_offset_y) * self.scale)

                color = (10,10,50)
                # Déterminer la couleur en fonction du biome
                for biome in self.config['biomes']:
                    if tile_type == biome['name']:
                        color = biome['color']
                        break

                pygame.draw.rect(self.screen, color, pygame.Rect(screen_x, screen_y, self.scale, self.scale))

        if draw_chunk:
            # Afficher les bordures des chunks
            chunk_border_color = (255, 255, 255)
            pygame.draw.rect(self.screen, chunk_border_color, 
                            pygame.Rect((chunk.x_offset - self.world_offset_x) * self.scale, 
                                        (chunk.y_offset - self.world_offset_y) * self.scale, 
                                        chunk.chunk_size * self.scale, chunk.chunk_size * self.scale), 1)

    def render_pnj(self, screen_x, screen_y):
        """Affiche un PNJ avec un décalage par rapport à la caméra."""
        pygame.draw.circle(self.screen, (255, 0, 0), (screen_x, screen_y), int(self.scale // 2))