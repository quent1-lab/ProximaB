import json, pygame, uuid, perlin_noise, os, json, numpy as np
from chunk_ import Chunk
from shapely.geometry import Polygon,MultiPolygon
from shapely.ops import unary_union

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
        self.event_manager = self.__dict__.get("event_manager", None)
        
        self.chunk_file = f'data/chunks_{config["perlin"]['seed']}_{config["perlin"]['octaves']}.json'  # Fichier pour stocker les chunks
        self.init_loaded_chunks(config['initial_chunk_radius'])
        # self.load_chunks_from_file()
    
    def init_loaded_chunks(self, radius):
        """Charge un nombre initial de chunks dans le monde."""
        self.load_chunks_from_file()
        for i in range(-radius, radius + 1):
            for j in range(-radius, radius + 1):
                self.get_chunk(i, j)
        self.save_chunks_to_file()
    
    def save_chunks_to_file(self):
        """Enregistre seulement les chunks modifiés dans un fichier."""
        if os.path.exists(self.chunk_file):
            with open(self.chunk_file, 'r') as f:
                try:
                    existing_chunks_data = json.load(f)
                except json.JSONDecodeError:
                    existing_chunks_data = {}
        else:
            existing_chunks_data = {}

        new_chunks_data = {}
        for chunk_coords, chunk in self.loaded_chunks.items():
            chunk_key = f"{chunk_coords[0]}_{chunk_coords[1]}"
            chunk_data = chunk.to_dict()
            if chunk_key not in existing_chunks_data or existing_chunks_data[chunk_key] != chunk_data:
                new_chunks_data[chunk_key] = chunk_data

        if new_chunks_data:
            existing_chunks_data.update(new_chunks_data)
            with open(self.chunk_file, 'w') as f:
                json.dump(existing_chunks_data, f)

    def load_chunks_from_file(self):
        """Charge tous les chunks à partir d'un fichier."""
        if os.path.exists(self.chunk_file):
            if os.path.getsize(self.chunk_file) == 0:
                print(f"Le fichier {self.chunk_file} est vide.")
                return
            try:
                with open(self.chunk_file, 'r') as f:
                    chunks_data = json.load(f)
                    for key, data in chunks_data.items():
                        chunk_x, chunk_y = map(int, key.split('_'))
                        self.loaded_chunks[(chunk_x, chunk_y)] = Chunk.from_dict(data, self.noise_generator, self.config, self.chunk_lock, self.entity_lock)
            except json.JSONDecodeError as e:
                print(f"Erreur de décodage JSON pour le fichier {self.chunk_file} : {e}")
                # Supprimer le fichier
                os.remove(self.chunk_file)
        else:
            print(f"Le fichier {self.chunk_file} n'existe pas.")
    
    def add_entity(self, entity):
        """Ajoute une entité au monde."""
        entity.register_for_events()
        
        if entity.entity_type not in self.entities:
            self.entities[entity.entity_type] = []
        self.entities[entity.entity_type].append(entity)
        
        # Mettre à jour la quantité d'entités dans le chunk
        chunk_x = int(entity.x) // self.config['chunk_size']
        chunk_y = int(entity.y) // self.config['chunk_size']
        chunk = self.get_chunk(chunk_x, chunk_y)
        chunk.add_entity(entity.entity_type)

    def add_entity_to_tile(self, tile):
        """Ajoute une entité à une tuile et l'enregistre dans la liste."""
        tile.set_entity_presence(True)
        if tile not in self.tiles_with_entities:
            self.tiles_with_entities.append(tile)

    def entity_is_present(self):
        """Vérifie si une entité est présente sur une tuile, et met à jour la tuile en conséquence."""
        for entity_list in self.entities.values():
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

    def drop_item_in_world(self, entity, item_name, quantity=1):
        chunk = self.get_chunk((entity.x, entity.y))
        entity.drop_item(item_name, chunk, quantity)
    
    def generate_id(self):
        """Génère un ID unique pour une entité."""
        return str(uuid.uuid1())
    
    def get_chunk(self, chunk_x, chunk_y):
        """Retourne un chunk, le génère si nécessaire."""
        if (chunk_x, chunk_y) not in self.loaded_chunks:
            # Générer et stocker le chunk s'il n'existe pas encore
            self.loaded_chunks[(chunk_x, chunk_y)] = Chunk(chunk_x, chunk_y , self.noise_generator, self.config, chunk_lock=self.chunk_lock, entity_lock=self.entity_lock)
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
    
    def get_chunk_from_position(self, x, y):
        """Retourne le chunk contenant les coordonnées (x, y)."""
        chunk_x = int(x) // self.config['chunk_size']
        chunk_y = int(y) // self.config['chunk_size']
        return self.get_chunk(chunk_x, chunk_y)
    
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

    def get_tile_at(self, x, y):
        """Retourne le type de terrain pour les coordonnées globales (x, y)."""
        chunk_x = int(x) // self.config['chunk_size']
        chunk_y = int(y) // self.config['chunk_size']
        chunk = self.get_chunk(chunk_x, chunk_y)
        
        # Calculer les coordonnées locales dans le chunk
        local_x = int(x) % self.config['chunk_size']
        local_y = int(y) % self.config['chunk_size']
        return chunk.tiles[local_x][local_y]
    
    # def get_resources_in_range(self, x, y, radius):
    #     """Retourne les ressources spécifiques dans un rayon autour de (x, y)."""
    #     resources = {}
    #     radius_chunk = radius // self.config['chunk_size'] + 1
    #     for chunk in self.get_chunks_around(x, y, radius_chunk):
    #         for row in chunk.tiles:
    #             for tile in row:
    #                 if tile.distance_to(x, y) <= radius:
    #                     if tile.biome:  # Assurez-vous que la tuile a une ressource
    #                         x_world = tile.x + chunk.x_offset
    #                         y_world = tile.y + chunk.y_offset
    #                         resources[tile.biome] = (x_world, y_world)
    #     return resources
    
    def get_tiles_in_range(self, x, y, radius):
        """Retourne les tuiles dans un rayon donné autour des coordonnées (x, y)."""
        resources = []
        radius_chunk = radius // self.config['chunk_size'] + 1
        chunks_around = self.get_chunks_around(x, y, radius_chunk)
        
        # print(f"Chunks around ({x}, {y}) with radius {radius}: {len(chunks_around)} chunks")

        for chunk in chunks_around:
            chunk_x_offset = chunk.x_offset
            chunk_y_offset = chunk.y_offset
            # print(f"Processing chunk at offset ({chunk_x_offset}, {chunk_y_offset})")

            for row in chunk.tiles:
                for tile in row:
                    x_world = tile.x + chunk_x_offset
                    y_world = tile.y + chunk_y_offset

                    distance = np.sqrt((x_world - x) ** 2 + (y_world - y) ** 2)
                    if distance <= radius:
                        if tile.biome not in resources:
                            resources[tile.biome] = [(x_world, y_world)]
                        else:
                            resources[tile.biome].append((x_world, y_world))
        print(f"Resources in range: {resources}")
        return resources

    def pick_up_item_in_world(self, entity, item_name, quantity=1):
        chunk = self.get_chunk((entity.x, entity.y))
        return entity.pick_up_item(chunk, item_name, quantity)

    def remove_entity_from_tile(self, tile):
        """Retire une entité d'une tuile."""
        tile.set_entity_presence(False)
        if tile in self.tiles_with_entities:
            self.tiles_with_entities.remove(tile)
    
    def remove_entity(self, entity):
        """Supprime une entité du monde."""
        for key, entity_list in self.entities.items():
            if entity in entity_list:
                self.entities[key].remove(entity)
   
    def search_for_entities(self, x, y, radius, entity_type):
        """Recherche des entités dans un rayon donné autour des coordonnées (x, y)."""
        entities_in_radius = []
        for entity in self.entities[entity_type]:
            distance = np.sqrt((entity.x - x) ** 2 + (entity.y - y) ** 2)
            if distance <= radius:
                entities_in_radius.append(entity)
        return entities_in_radius
    
    def update_entities(self, delta_time):
        """Met à jour toutes les entités du monde."""
        entity_keys = list(self.entities.keys())
        for entity_type in entity_keys:
            entity_list = self.entities.get(entity_type, [])
            for entity in entity_list:
                entity.update(delta_time)
        
        # Vérifier la présence des entités sur les tuiles
        self.entity_is_present()
        
        # Vérifier la présence des entités sur les tuiles
        self.entity_is_not_present()

# ======================================================================================
# ================================= Class CAMERA =======================================
# ======================================================================================

class Camera:
    """Classe gérant la caméra comme entité invisible et fixe, les chunks se déplacent autour d'elle."""
    def __init__(self, world, config, mode="free", start_x=0, start_y=0):
        self.world = world
        self.config = config
        self.mode = mode
        self.target_pnj = None  # PNJ à suivre

        # Coordonnées du centre de la caméra dans le monde
        self.camera_center_x = start_x
        self.camera_center_y = start_y

        # Échelle initiale (zoom de base)
        self.scale = config['scale']
        self.chunk_size = config['chunk_size']
        self.zoom_speed = 0.5  # Vitesse de zoom

        # Dimensions de l'écran
        self.screen_width = config['screen_width']
        self.screen_height = config['screen_height']
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        self.font = pygame.font.Font(None, 24)

        # Position précédente de la caméra pour détecter le mouvement
        self.previous_camera_position = (-1, -1)

    def set_mode(self, mode, target_pnj=None):
        """Définit le mode de la caméra (fixe, libre ou suivi d'un PNJ)."""
        self.mode = mode
        if mode == "follow":
            self.target_pnj = target_pnj

    def has_camera_moved(self):
        current_position = (self.camera_center_x, self.camera_center_y)
        if current_position != self.previous_camera_position:
            self.previous_camera_position = current_position
            return True
        return False

    def entity_has_moved(self):
        # Vérifier si une entité a bougé 
        for entity_list in self.world.entities.values():
            for entity in entity_list:
                return entity.has_moved()

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
            self.camera_center_x = self.target_pnj.x
            self.camera_center_y = self.target_pnj.y

    def move(self, dx, dy):
        """Déplace la caméra en fonction du déplacement."""
        self.camera_center_x += dx / self.scale
        self.camera_center_y += dy / self.scale

    def handle_zoom(self):
        """Gère le zoom dynamique avec la molette de la souris."""
        zoom_in = False
        zoom_out = False

        keys = pygame.key.get_pressed()
        if keys[pygame.K_a]:
            zoom_in = True
        if keys[pygame.K_e]:
            zoom_out = True
        if keys[pygame.K_r]:
            self.scale = self.config['scale']
            self.camera_center_x = self.config['screen_width'] // 2
            self.camera_center_y = self.config['screen_height'] // 2

        mouse_x, mouse_y = pygame.mouse.get_pos()
        world_mouse_x = mouse_x / self.scale + self.camera_center_x - self.screen_width / (2 * self.scale)
        world_mouse_y = mouse_y / self.scale + self.camera_center_y - self.screen_height / (2 * self.scale)

        if zoom_in:
            self.scale += self.zoom_speed
        if zoom_out and self.scale > self.zoom_speed:  # Empêcher un zoom trop petit
            self.scale -= self.zoom_speed

        new_world_mouse_x = mouse_x / self.scale + self.camera_center_x - self.screen_width / (2 * self.scale)
        new_world_mouse_y = mouse_y / self.scale + self.camera_center_y - self.screen_height / (2 * self.scale)

        self.camera_center_x += world_mouse_x - new_world_mouse_x
        self.camera_center_y += world_mouse_y - new_world_mouse_y

    def greedy_mesh_parallel(self, visible_tiles_by_chunk):
        """Optimisation en utilisant plusieurs threads pour traiter plusieurs chunks en parallèle."""
        rectangles = []
        
        # def process_chunk(chunk_data):
        #     """Exécuter le greedy meshing sur un chunk donné."""
        #     return self.greedy_mesh_optimized(chunk_data)

        # with concurrent.futures.ThreadPoolExecutor() as executor:
        #     futures = [executor.submit(process_chunk, chunk) for chunk in visible_tiles_by_chunk]
        #     for future in concurrent.futures.as_completed(futures):
        #         rectangles.extend(future.result())

        # return rectangles

    def render(self):
        """Affiche le monde et les PNJ avec déplacement du décor en fonction de la caméra."""
        # self.screen.fill((135, 206, 235))  # Fond bleu ciel

        # Récupère tous les chunks visibles
        visible_chunks = self.get_visible_chunks()
        
        rectangles = []
        items = []
        
        for chunk in visible_chunks:
            chunk_x, chunk_y = chunk
            chunk = self.world.get_chunk(chunk_x, chunk_y)
            rectangle = chunk.calculate_mesh(self.greedy_mesh_chunk)
            items.append(chunk.dropped_items)
            
            # Ajouter l'offset du chunk pour le rendu
            for x, y, w, h, tile_type in rectangle:
                rectangles.append((x + chunk_x * self.chunk_size, y + chunk_y * self.chunk_size, w, h, tile_type))

        # Rendre les rectangles optimisés
        self.render_rectangles(rectangles)
        
        # Affichage des items droppés
        for dropped_items in items:
            for dropped_item in dropped_items:
                # Affichage en fonction de la position dans le monde et de la position de la caméra
                screen_x = int((dropped_item.position[0] - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale)
                screen_y = int((dropped_item.position[1] - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                # Remplacer par un affichage de sprite ou autre représentation visuelle
                dropped_item.item.render(self.screen, screen_x, screen_y, scale=self.scale)
        
        # Afficher les PNJ
        for entity_list in self.world.entities.values():
            for entity in entity_list:
                screen_x = int((entity.x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale)
                screen_y = int((entity.y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                entity.render(self.screen, self.scale, screen_x, screen_y)

                # Afficher la zone découverte par le PNJ
                if entity.entity_type == "PNJ":
                    if entity.memory:
                        chunks = entity.memory.get_all_discovered_chunks()
                        # A partir des chunk découvert, afficher un polygone des bordures des chunks découverts
                        polygons = []
                        for chunk in chunks:
                            chunk_x, chunk_y = chunk
                            x = chunk_x * self.chunk_size
                            y = chunk_y * self.chunk_size
                            # Créer un polygone pour chaque chunk
                            chunk_polygon = Polygon([
                                (x, y),
                                (x + self.chunk_size, y),
                                (x + self.chunk_size, y + self.chunk_size),
                                (x, y + self.chunk_size)
                            ])
                            polygons.append(chunk_polygon)
                        
                        if polygons:
                            if isinstance(polygons, MultiPolygon):
                                polygons = polygons.geoms   

                            unified_polygon = unary_union(polygons)
                            
                            # Vérifier si le résultat est un Polygon ou un MultiPolygon
                            if isinstance(unified_polygon, Polygon):
                                # Convertir les points en coordonnées d'écran
                                screen_points = [
                                    (
                                        int((x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                        int((y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                                    )
                                    for x, y in unified_polygon.exterior.coords
                                ]
                                pygame.draw.polygon(self.screen, entity.color, screen_points, 1)

                            elif isinstance(unified_polygon, MultiPolygon):
                                for polygon in unified_polygon.geoms:
                                    screen_points = [
                                        (
                                            int((x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                            int((y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                                        )
                                        for x, y in polygon.exterior.coords
                                    ]
                                    pygame.draw.polygon(self.screen, entity.color, screen_points, 1)

                            else:
                                print("Aucun polygone valide pour l'entité.")
                            
                
                    # Afficher la zone visible par le PNJ
                    if entity.vision_range > 0:
                        # Affiche le cone de vision en fonction de l'angle de vue
                        vision_polygon = entity.get_vision_polygon()
                        if vision_polygon:
                            # Obtenir les points du polygone
                            points = list(vision_polygon.exterior.coords)
                            # Ajouter les coordonnées du PNJ (centre du cône de vision)
                            pnj_position = (entity.x, entity.y)
                            
                            # Convertir les points en coordonnées d'écran
                            screen_points = [
                                (
                                    int((x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                    int((y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                                )
                                for x, y in points
                            ]
                            screen_points.pop(-1)
                            screen_points.append((
                                int((pnj_position[0] - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                int((pnj_position[1] - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                            ))  
                            # Créer une surface avec un canal alpha (transparence)
                            transparent_surface = pygame.Surface((self.screen_width, self.screen_height), pygame.SRCALPHA)
                            
                            # Dessiner le polygone sur la surface transparente
                            pygame.draw.polygon(transparent_surface, (255, 255, 0, 100), screen_points)
                            
                            # Blitter la surface transparente sur l'écran principal
                            self.screen.blit(transparent_surface, (0, 0))
                            
                    # Afficher la cible du PNJ
                    if entity.target_location:
                        x, y = entity.target_location
                        t_screen_x = int((x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale)
                        t_screen_y = int((y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                        if entity.path:
                            for i in range(len(entity.path) - 1):
                                x1, y1 = entity.path[i]
                                x2, y2 = entity.path[i + 1]
                                p1 = (
                                    int((x1 - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                    int((y1 - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                                )
                                p2 = (
                                    int((x2 - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                    int((y2 - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                                )
                                if i == 0:
                                    pygame.draw.line(self.screen, (100, 255, 0), (screen_x, screen_y), p1, 2)
                                elif i == len(entity.path) - 2:
                                    pygame.draw.line(self.screen, (100, 255, 0), p2, (t_screen_x, t_screen_y), 2)
                                pygame.draw.line(self.screen, (100, 255, 0), p1, p2, 2)
                        else:
                            pygame.draw.line(self.screen, (100, 255, 0), (screen_x, screen_y), (t_screen_x, t_screen_y), 2)
                        pygame.draw.circle(self.screen, (255, 0, 255), (t_screen_x, t_screen_y), self.scale // 2)
                    
                    if entity.path:
                        for i in range(len(entity.path) - 1):
                            x1, y1 = entity.path[i]
                            x2, y2 = entity.path[i + 1]
                            p1 = (
                                int((x1 - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                int((y1 - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                            )
                            p2 = (
                                int((x2 - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale),
                                int((y2 - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale)
                            )
                            pygame.draw.line(self.screen, (100, 255, 0), p1, p2, 2)
        
        # Ecriture du nombre de chunks chargés
        text = self.font.render(f"Chunks loaded: {len(self.world.loaded_chunks)}", True, (255, 255, 255))
        self.screen.blit(text, (10, 40))
    
    def get_visible_tiles(self):
        """Récupère toutes les tuiles des chunks visibles avec leurs coordonnées globales."""
        half_screen_width = self.screen_width / 2  # Utiliser une division flottante
        half_screen_height = self.screen_height / 2

        camera_world_x = self.camera_center_x
        camera_world_y = self.camera_center_y

        # Limites exactes en flottant
        left_bound = camera_world_x - half_screen_width / self.scale
        right_bound = camera_world_x + half_screen_width / self.scale
        top_bound = camera_world_y - half_screen_height / self.scale
        bottom_bound = camera_world_y + half_screen_height / self.scale

        # Calcule des chunks visibles
        left_chunk = int(left_bound // self.chunk_size)
        right_chunk = int(right_bound // self.chunk_size)
        top_chunk = int(top_bound // self.chunk_size)
        bottom_chunk = int(bottom_bound // self.chunk_size)

        visible_tiles = {}
        for chunk_x in range(left_chunk, right_chunk + 1):
            for chunk_y in range(top_chunk, bottom_chunk + 1):
                chunk = self.world.get_chunk(chunk_x, chunk_y)
                if chunk:
                    for row in chunk.tiles:
                        for tile in row:
                            global_x = tile.x + chunk_x / self.chunk_size
                            global_y = tile.y + chunk_y / self.chunk_size
                            visible_tiles[(global_x, global_y)] = tile
                            
        # Détermine la largeur et la hauteur du monde visible
        width = int(right_bound - left_bound)
        height = int(bottom_bound - top_bound)

        return visible_tiles, width, height

    def get_visible_chunks(self):
        """Récupère tous les chunks visibles avec leurs coordonnées globales."""
        half_screen_width = self.screen_width / 2  # Utiliser une division flottante
        half_screen_height = self.screen_height / 2

        camera_world_x = self.camera_center_x
        camera_world_y = self.camera_center_y

        # Limites exactes en flottant
        left_bound = camera_world_x - half_screen_width / self.scale
        right_bound = camera_world_x + half_screen_width / self.scale
        top_bound = camera_world_y - half_screen_height / self.scale
        bottom_bound = camera_world_y + half_screen_height / self.scale

        # Calcule des chunks visibles
        left_chunk = int(left_bound // self.chunk_size)
        right_chunk = int(right_bound // self.chunk_size)
        top_chunk = int(top_bound // self.chunk_size)
        bottom_chunk = int(bottom_bound // self.chunk_size)

        visible_chunks = []
        for chunk_x in range(left_chunk, right_chunk + 1):
            for chunk_y in range(top_chunk, bottom_chunk + 1):
                visible_chunks.append((chunk_x, chunk_y))
        
        return visible_chunks

    def greedy_mesh(self, tiles):
        """Applique l'algorithme de greedy meshing sur les tuiles visibles."""
        if not tiles:
            return []

        visited = set()
        rectangles = []

        for (global_x, global_y), tile in tiles.items():
            if (global_x, global_y) in visited:
                continue

            tile_type = tile.biome
            width, height = 1, 1

            # Trouver la largeur maximale
            while (global_x + width, global_y) in tiles and tiles[(global_x + width, global_y)].biome == tile_type and (global_x + width, global_y) not in visited:
                width += 1

            # Trouver la hauteur maximale
            while all((global_x + w, global_y + height) in tiles and tiles[(global_x + w, global_y + height)].biome == tile_type and (global_x + w, global_y + height) not in visited for w in range(width)):
                height += 1

            # Marquer les tuiles comme visitées
            for dy in range(height):
                for dx in range(width):
                    visited.add((global_x + dx, global_y + dy))

            # Ajouter le rectangle à la liste
            rectangles.append((global_x, global_y, width, height, tile_type))

        return rectangles

    def greedy_mesh_optimized(self, tiles):
        """Optimisation du greedy meshing avec balayage horizontal."""
        if not tiles:
            return []

        visited = set()
        rectangles = []

        for (global_x, global_y), tile in tiles.items():
            if (global_x, global_y) in visited:
                continue

            tile_type = tile.biome
            width, height = 1, 1

            # Étendre en largeur tant que les tuiles adjacentes sont du même type
            while (global_x + width, global_y) in tiles and tiles[(global_x + width, global_y)].biome == tile_type and (global_x + width, global_y) not in visited:
                width += 1

            # Étendre verticalement si toutes les tuiles dans la rangée ont le même type
            extendable = True
            while extendable:
                for dx in range(width):
                    if (global_x + dx, global_y + height) not in tiles or tiles[(global_x + dx, global_y + height)].biome != tile_type or (global_x + dx, global_y + height) in visited:
                        extendable = False
                        break
                if extendable:
                    height += 1

            # Marquer les tuiles fusionnées comme visitées
            for dy in range(height):
                for dx in range(width):
                    visited.add((global_x + dx, global_y + dy))

            # Ajouter le rectangle à la liste des rectangles fusionnés
            rectangles.append((global_x, global_y, width, height, tile_type))

        return rectangles

    def greedy_mesh_chunk(self, tiles):
        """Applique l'algorithme de greedy meshing sur les tuiles d'un chunk."""
        chunk_size = len(tiles)
        visited = [[False] * chunk_size for _ in range(chunk_size)]
        rectangles = []

        for x in range(chunk_size):
            for y in range(chunk_size):
                if visited[x][y]:
                    continue

                tile_type = tiles[x][y].biome
                width, height = 1, 1

                # Étendre en largeur tant que les tuiles adjacentes sont du même type
                while x + width < chunk_size and tiles[x + width][y].biome == tile_type and not visited[x + width][y]:
                    width += 1

                # Étendre verticalement si toutes les tuiles dans la rangée ont le même type
                extendable = True
                while extendable:
                    for dx in range(width):
                        if y + height >= chunk_size or tiles[x + dx][y + height].biome != tile_type or visited[x + dx][y + height]:
                            extendable = False
                            break
                    if extendable:
                        height += 1

                # Marquer les tuiles comme visitées
                for dx in range(width):
                    for dy in range(height):
                        visited[x + dx][y + dy] = True

                # Ajouter le rectangle à la liste
                rectangles.append((x, y, width, height, tile_type))

        return rectangles
            
    def render_visible_tiles(self, tiles):
        """Rend les tuiles visibles."""
        for (global_x, global_y), tile in tiles.items():
            screen_x = (global_x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale
            screen_y = (global_y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale
            screen_width = self.scale
            screen_height = self.scale

            # Déterminer la couleur en fonction du biome
            color = (10, 10, 50)
            for biome in self.config['biomes']:
                if tile.biome == biome['name']:
                    color = biome['color']
                    break

            # Dessiner la tuile
            pygame.draw.rect(self.screen, color, pygame.Rect(screen_x, screen_y, screen_width, screen_height))
            pygame.draw.rect(self.screen, (100,100, 100), pygame.Rect(screen_x, screen_y, screen_width, screen_height), 1)

    def render_rectangles(self, rectangles):
        """Rend les rectangles optimisés."""
        for rect in rectangles:
            global_x, global_y, width, height, tile_type = rect

            # Calcule en flottant avant conversion
            screen_x = (global_x - self.camera_center_x + self.screen_width / 2 / self.scale) * self.scale
            screen_y = (global_y - self.camera_center_y + self.screen_height / 2 / self.scale) * self.scale
            screen_width = width * self.scale
            screen_height = height * self.scale

            # Convertir en entier uniquement pour le rendu
            screen_x = int(np.ceil(screen_x))
            screen_y = int(np.ceil(screen_y))
            screen_width = int(np.ceil(screen_width))
            screen_height = int(np.ceil(screen_height))

            # Déterminer la couleur en fonction du biome
            color = (10, 10, 50)
            for biome in self.config['biomes']:
                if tile_type == biome['name']:
                    color = biome['color']
                    break

            # Dessiner le rectangle sans marge ajoutée
            
            pygame.draw.rect(self.screen, color, pygame.Rect(screen_x, screen_y, screen_width+1, screen_height+1))
            # pygame.draw.rect(self.screen, (100,100,100), pygame.Rect(screen_x, screen_y, screen_width, screen_height), 1)
